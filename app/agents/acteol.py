import enum
import json
from decimal import Decimal
from http import HTTPStatus
from typing import Dict, List
from urllib.parse import urljoin

import arrow
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    JOIN_ERROR,
    NO_SUCH_RECORD,
    STATUS_LOGIN_FAILED,
    VALIDATION,
    AgentError,
    LoginError,
    RegistrationError,
)
from app.configuration import Configuration
from app.encryption import HashSHA1
from arrow import Arrow
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, logger
from tenacity import retry, stop_after_attempt, wait_exponential

RETRY_LIMIT = 3  # Number of times we should attempt another Acteol API call on failure


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1
    STAMPS = 2


class Acteol(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.credentials = user_info["credentials"]
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        self.token_store = UserTokenStore(REDIS_URL)
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    # Public methods
    def authenticate(self) -> Dict:
        """
        Get an API token from redis if we have one, otherwise login to get one and store in cache.
        This token is not per-user, it is for our backend to use their API

        :return: valid token dict
        """
        have_valid_token = False  # Assume no good token to begin with
        current_timestamp = arrow.utcnow().timestamp
        token = {}
        try:
            token: Dict = json.loads(self.token_store.get(self.scheme_id))
            try:  # Token may be in bad format and needs refreshing
                if self._token_is_valid(
                    token=token, current_timestamp=current_timestamp
                ):
                    have_valid_token = True
            except (KeyError, TypeError) as e:
                logger.exception(e)  # have_valid_token is still False
        except (KeyError, self.token_store.NoSuchToken):
            pass  # have_valid_token is still False

        if not have_valid_token:
            acteol_access_token = self._refresh_access_token()
            token = self._store_token(
                acteol_access_token=acteol_access_token,
                current_timestamp=current_timestamp,
            )

        return token

    def register(self, credentials: Dict):
        """
        Register a new loyalty scheme member with Acteol. The steps are:
        * Get API token
        * Check if account already exists
        * If not, create account
        * Use the CtcID from create account to add member number in Acteol
        * Get the customer details from Acteol
        * Post user preferences (marketing email opt-in) to Acteol
        * Use the customer details in Bink system
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()
        # Create an origin id for subsequent API calls
        user_email = credentials["email"]
        origin_id = self._create_origin_id(
            user_email=user_email, origin_root=self.ORIGIN_ROOT
        )

        # Check if account already exists
        account_already_exists = self._account_already_exists(origin_id=origin_id)
        if account_already_exists:
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)  # The join journey ends

        # The account does not exist, so we can create one
        ctcid = self._create_account(origin_id=origin_id, credentials=credentials)

        # Add the new member number to Acteol
        member_number = self._add_member_number(ctcid=ctcid)

        # Get customer details
        customer_details = self._get_customer_details(origin_id=origin_id)
        if not self._customer_fields_are_present(customer_details=customer_details):
            logger.debug(
                (
                    "Expected fields not found in customer details during join: Email, CurrentMemberNumber, CustomerID "
                    f"for user email: {user_email}"
                )
            )
            raise RegistrationError(JOIN_ERROR)

        # Set user's email opt-in preferences in Acteol
        email_optin_pref: bool = self._get_email_optin_pref_from_consent(
            consents=credentials.get("consents", [{}])
        )
        # Not a fatal error if we can't register i.e. don't kill the join process, just log
        try:
            self._set_customer_preferences(
                ctcid=ctcid, email_optin_pref=email_optin_pref
            )
        except AgentError as ae:
            logger.info(f"AgentError while setting customer preferences: {ae.message}")
        except Exception as e:
            logger.info(f"Exception while setting customer preferences: {str(e)}")

        # Set up instance attributes that will result in the creation of an active membership card
        self.identifier = {
            "card_number": member_number,
            "merchant_identifier": ctcid,
        }
        self.user_info["credentials"].update(self.identifier)

    def balance(self) -> Dict:
        """
        Get the balance from the Acteol API, return the expected format. For the vouchers element, these fields are
        expected by hermes:
        * issue_date: int, optional
        * redeem_date: int, optional
        * expiry_date: int, optional
        * code: str, optional
        * type: int, required
        * value: Decimal, optional
        * target_value: Decimal, optional

        :return: balance data including vouchers
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()
        # Create an origin id for subsequent API calls, using credentials created during instantiation
        user_email = self.credentials["email"]
        origin_id = self._create_origin_id(
            user_email=user_email, origin_root=self.ORIGIN_ROOT
        )

        # Get customer details
        customer_details = self._get_customer_details(origin_id=origin_id)
        if not self._customer_fields_are_present(customer_details=customer_details):
            logger.debug(
                (
                    "Expected fields not found in customer details during join: Email, CurrentMemberNumber, CustomerID "
                    f"for user email: {user_email}"
                )
            )
            raise AgentError(NO_SUCH_RECORD)

        points = Decimal(customer_details["LoyaltyPointsBalance"])

        # Make sure we have a populated merchant_identifier in credentials. This is required to get voucher
        # data from Acteol. If it's not already present in the credentials then populate that field from
        # the customer_details - do this so that we have a full record of credentials for anything else that might
        # rely on it.
        if not self.credentials.get("merchant_identifier"):
            self.credentials["merchant_identifier"] = customer_details["CustomerID"]
        ctcid = self.credentials["merchant_identifier"]
        # Get all vouchers for this customer
        vouchers: List = self._get_vouchers(ctcid=ctcid)
        # Filter for BINK only vouchers
        bink_only_vouchers = self._filter_bink_vouchers(vouchers=vouchers)
        bink_mapped_vouchers = []  # Vouchers mapped to format required by Bink
        for bink_only_voucher in bink_only_vouchers:
            bink_mapped_voucher: Dict = self._map_acteol_voucher_to_bink_struct(
                voucher=bink_only_voucher
            )
            bink_mapped_vouchers.append(bink_mapped_voucher)
        # Lastly, create an 'in-progress' voucher - the current, incomplete voucher
        in_progress_voucher = self._make_in_progress_voucher(
            points=points, voucher_type=VoucherType.STAMPS
        )
        bink_mapped_vouchers.append(in_progress_voucher)

        balance = {
            "points": points,
            "value": points,
            "value_label": "",
            "vouchers": bink_mapped_vouchers,
        }

        return balance

    def parse_transaction(self, transaction: Dict) -> Dict:
        """
        Convert an individual transaction record from Acteol's system to the format expected by Bink

        :param transaction: a transaction record
        :return: transaction record in the format required by Bink
        """
        formatted_total_cost = self._format_money_value(
            money_value=transaction["TotalCost"]
        )

        order_date = arrow.get(transaction["OrderDate"])
        points = int(transaction["PointEarned"])
        description = self._make_transaction_description(
            location_name=transaction["LocationName"],
            formatted_total_cost=formatted_total_cost,
        )
        location = transaction["LocationName"]

        parsed_transaction = {
            "date": order_date,
            "description": description,
            "points": points,
            "location": location,
        }

        return parsed_transaction

    def scrape_transactions(self) -> List[Dict]:
        """
        We're not scraping, we're calling the Acteol API

        :return: list of transaction dicts from Acteol's API
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()

        ctcid: str = self.credentials["merchant_identifier"]
        api_url = urljoin(
            self.base_url,
            f"api/Order/Get?CtcID={ctcid}&LastRecordsCount={self.N_TRANSACTIONS}&IncludeOrderDetails=false",
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        transactions: List[Dict] = resp.json()

        return transactions

    def get_contact_ids_by_email(self, email: str) -> Dict:
        """
        Get dict of contact ids from Acteol by email

        :param email: user's email address
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()

        api_url = urljoin(
            self.base_url, f"api/Contact/GetContactIDsByEmail?Email={email}"
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        resp.raise_for_status()
        contact_ids_data = resp.json()

        return contact_ids_data

    def delete_contact_by_ctcid(self, ctcid: str):
        """
        Delete a customer by their CtcID (aka CustomerID)
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()

        api_url = urljoin(self.base_url, f"api/Contact/DeleteContact/{ctcid}")
        resp = self.make_request(api_url, method="delete", timeout=self.API_TIMEOUT)

        return resp

    def login(self, credentials) -> None:
        """
        Acteol works slightly differently to some other agents, as we must authenticate() before each call to
        ensure our API token is still valid / not expired. See authenticate()
        """
        # If we are on an add journey, then we will need to verify the supplied email against the card number
        if credentials["card_number"] and not self.user_info.get("from_register"):
            # Don't go any further unless the account is valid
            ctcid = self._validate_member_number(credentials)
            self.identifier_type = (
                "card_number"  # Not sure this is needed but the base class has one
            )
            # Set up attributes needed for the creation of an active membership card
            self.identifier = {
                "card_number": credentials["card_number"],
                "merchant_identifier": ctcid,
            }
            credentials.update({"merchant_identifier": ctcid})

        # Ensure credentials are available via the instance
        self.credentials = credentials

        return

    # Private methods
    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_customer_details(self, origin_id: str) -> Dict:
        """
        Get the customer details from Acteol

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        """
        api_url = urljoin(
            self.base_url,
            (
                "api/Loyalty/GetCustomerDetailsByExternalCustomerID"
                f"?externalcustomerid={origin_id}&partnerid=BinkPlatform"
            ),
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)

        if resp.status_code != HTTPStatus.OK:
            logger.debug(
                f"Error while fetching customer details, reason: {resp.reason}"
            )
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        customer_details_data = resp.json()

        return customer_details_data

    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _account_already_exists(self, origin_id: str) -> bool:
        """
        Check if account already exists in Acteol

        FindByOriginID will return HTTPStatus.OK and an empty list if the account does NOT exist.
        It will return HTTPStatus.OK and details in the json if the account exists.
        All other responses (including 3xx/5xx) should be caught and the card ends up in a failed state

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        """
        api_url = urljoin(
            self.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}"
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)

        if resp.status_code != HTTPStatus.OK:
            logger.debug(
                f"Error while checking for existing account, reason: {resp.reason}"
            )
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        response_json = resp.json()
        if response_json:
            return True

        return False

    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _create_account(self, origin_id: str, credentials: Dict) -> str:
        """
        Create an account in Acteol

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        :param credentials: dict of user's credentials
        """
        api_url = urljoin(self.base_url, "api/Contact/PostContact")
        payload = {
            "OriginID": origin_id,
            "SourceID": "BinkPlatform",
            "FirstName": credentials["first_name"],
            "LastName": credentials["last_name"],
            "Email": credentials["email"],
            "Phone": credentials.get("phone", ""),
            "Company": {"PostCode": credentials.get("postcode", "")},
        }
        resp = self.make_request(
            api_url, method="post", timeout=self.API_TIMEOUT, json=payload
        )

        if resp.status_code != HTTPStatus.OK:
            logger.debug(f"Error while creating new account, reason: {resp.reason}")
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        response_json = resp.json()
        ctcid = response_json["CtcID"]

        return ctcid

    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _add_member_number(self, ctcid: str) -> str:
        """
        Add member number to Acteol

        :param ctcid: ID returned from Acteol when creating the account
        """
        api_url = urljoin(self.base_url, f"api/Contact/AddMemberNumber?CtcID={ctcid}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)

        if resp.status_code != HTTPStatus.OK:
            logger.debug(f"Error while adding member number, reason: {resp.reason}")
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        member_number = resp.json()["MemberNumber"]

        return member_number

    @staticmethod
    def _make_headers(token: str):
        return {"Authorization": f"Bearer {token}"}

    def _create_origin_id(self, user_email: str, origin_root: str):
        """
        our origin id should be in the form of SHA1("Bink-company-user_email")

        :param user_email: our user's email
        :param origin_root: set in this class's subclass per the requirements of the API for each company
        """
        origin_id = HashSHA1().encrypt(f"{origin_root}-{user_email}")

        return origin_id

    def _token_is_valid(self, token: Dict, current_timestamp: int) -> bool:
        """
        Determine if our token is still valid, based on whether the difference between the current timestamp
        and the token's timestamp is less than the configured timeout in seconds

        :param token: Dict of token data
        :param current_timestamp: timestamp of current time from Arrow
        :return: Boolean
        """
        return (current_timestamp - token["timestamp"]) < self.AUTH_TOKEN_TIMEOUT

    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _refresh_access_token(self) -> str:
        """
        Returns an Acteol API auth token to use in subsequent requests.
        """
        payload = {
            "grant_type": "password",
            "username": self.auth["username"],
            "password": self.auth["password"],
        }
        token_url = urljoin(self.base_url, "token")
        resp = self.make_request(
            token_url, method="post", timeout=self.API_TIMEOUT, data=payload
        )
        token = resp.json()["access_token"]

        return token

    def _store_token(self, acteol_access_token: str, current_timestamp: int) -> Dict:
        """
        Create a full token, with timestamp, from the acteol access token

        :param acteol_access_token: A token given to us by logging into the Acteol API
        :param current_timestamp: Timestamp (Arrow) of the current UTC time
        :return: The created token dict
        """
        token = {
            "acteol_access_token": acteol_access_token,
            "timestamp": current_timestamp,
        }
        self.token_store.set(scheme_account_id=self.scheme_id, token=json.dumps(token))

        return token

    def _customer_fields_are_present(self, customer_details: Dict) -> bool:
        """
        These fields are required and expected, so it's an exception if they're not there
        """
        return all(
            [
                k in customer_details
                for k in ["Email", "CurrentMemberNumber", "CustomerID"]
            ]
        )

    # Retry on any Exception at 3, 3, 6, 12 seconds, stopping at RETRY_LIMIT. Reraise the exception from make_request()
    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _set_customer_preferences(self, ctcid: str, email_optin_pref: bool):
        """
        Set user's email opt-in preferences in Acteol
        Condition: "EmailOptin" = true if Enrol user consent has been marked as true.

        :param email_optin_pref: boolean
        """
        api_url = urljoin(self.base_url, "api/CommunicationPreference/Post")
        payload = {
            "CustomerID": ctcid,
            "EmailOptin": email_optin_pref,
        }
        self.make_request(
            api_url, method="post", timeout=self.API_TIMEOUT, json=payload
        )

    def _get_email_optin_pref_from_consent(self, consents: List[Dict]) -> bool:
        """
        Find the dict (should only be one) with a key of EmailOptin that also has key of "value" set to True

        :param consents: the list of consents dicts from the user's credentials
        :return: bool True if at least one matching dict found
        """
        matching_true_consents = list(
            filter(
                lambda x: x.get("slug") == "EmailOptin" and bool(x.get("value")),
                consents,
            )
        )

        if matching_true_consents:
            return True

        return False

    def _validate_member_number(self, credentials: Dict) -> str:
        """
        Checks with Acteol to verify whether a loyalty account exists for this email and card number

        Invalid Card Number
            "IsValid": false AND "ValidationMsg": "Invalid Member Number" OR "Invalid Email"
            Action - membership_card Status=? Add data rejected by merchant, State=Failed and Reason Code=X102
            (for the front-end to handle) i.e. raise a VALIDATION exception

        Credentials do not match
            "IsValid": false AND "ValidationMsg": "Email and Member number mismatch"
            Action - membership_card Status=403 Invalid credentials, State=Failed and Reason Code=X303
            (for the front-end to handle i.e. raise a STATUS_LOGIN_FAILED exception

        :param credentials: dict of user's credentials, email etc
        :return: ctcid (aka CustomerID or merchant_identifier in Bink)
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()

        api_url = urljoin(self.base_url, "api/Contact/ValidateContactMemberNumber")
        member_number = credentials["card_number"]
        payload = {
            "MemberNumber": member_number,
            "Email": credentials["email"],
        }
        try:
            resp = self.make_request(
                api_url, method="get", timeout=self.API_TIMEOUT, json=payload
            )
        except AgentError as ae:
            logger.error(f"Error while validating card_number/MemberNumber: {str(ae)}")
            raise LoginError(STATUS_LOGIN_FAILED) from ae

        # It's possible for a 200 OK response to be returned, but validation has failed. Get the cause for logging.
        resp_json = resp.json()
        validation_msg = resp_json.get("ValidationMsg")
        is_valid = resp_json.get("IsValid")
        if not is_valid:
            validation_error_types = {
                "Invalid Email": VALIDATION,
                "Invalid Member Number": VALIDATION,
                "Email and Member number mismatch": STATUS_LOGIN_FAILED,
            }

            error_type = validation_error_types.get(validation_msg, STATUS_LOGIN_FAILED)
            logger.error(
                f"Failed login validation for member number {member_number}: {validation_msg}"
            )
            raise LoginError(error_type)

        ctcid = str(resp_json["CtcID"])

        return ctcid

    def _get_vouchers(self, ctcid: str) -> List:
        """
        Get all vouchers for a CustomerID (aka CtcID) from Acteol

        :param ctcid: CustomerID in Acteol and merchant_identifier in Bink
        :return: list of vouchers
        """
        # Ensure a valid API token
        self._get_valid_api_token_and_make_headers()

        api_url = urljoin(
            self.base_url, f"api/Voucher/GetAllByCustomerID?customerid={ctcid}"
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        response_json = resp.json()
        vouchers: List = response_json["voucher"]

        return vouchers

    def _filter_bink_vouchers(self, vouchers: List[Dict]) -> List[Dict]:
        """
        Filter for BINK only vouchers

        :param vouchers: list of voucher dicts from Acteol
        :return: only those voucher dicts whose CategoryName == "BINK"
        """
        bink_only_vouchers = [
            voucher for voucher in vouchers if voucher["CategoryName"] == "BINK"
        ]

        return bink_only_vouchers

    def _map_acteol_voucher_to_bink_struct(self, voucher: Dict) -> Dict:
        """
        Decide what state the voucher is in (Issued, Expired etc) and put it into the expected shape for that state.
        These are mutually exclusive states, the voucher should never be in more than one at any time:

        * Redeemed - if the agent returned a redeem date on the voucher then it's a redeemed voucher/there is a
        boolean that will be true if the voucher has a redeemed date
        * Issued - if the start date is set and the expiry date hasn't passed yet then it's issued,
        * Expired - otherwise it's expired.
        * Cancelled - there is a disabled flag, that if true means the voucher is cancelled and should not
        be displayed, but should be saved for the the user
        * In Progress
          Acteol only issue vouchers once the stamp card is complete.

        :param voucher: dict of a single voucher's data from Acteol
        :return: dict of voucher data mapped for Bink
        """

        current_datetime = arrow.now()

        # Is it a redeemed voucher?
        bink_voucher = self._make_redeemed_voucher(voucher=voucher)
        if bink_voucher:
            return bink_voucher
        # Is it a cancelled voucher?
        bink_voucher = self._make_cancelled_voucher(voucher=voucher)
        if bink_voucher:
            return bink_voucher
        # Is it an issued voucher?
        bink_voucher = self._make_issued_voucher(
            voucher=voucher, current_datetime=current_datetime
        )
        if bink_voucher:
            return bink_voucher
        # Is it expired?
        bink_voucher = self._make_expired_voucher(
            voucher=voucher, current_datetime=current_datetime
        )
        if bink_voucher:
            return bink_voucher

        logger.warning(
            f'Acteol voucher did not match any of the Bink structure criteria, voucher id: {voucher["VoucherID"]}'
        )

        return {}

    def _make_redeemed_voucher(self, voucher: Dict) -> [Dict, None]:
        """
        Make a Bink redeemed voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :return: dict of redeemed voucher data mapped for Bink, or None
        """

        if voucher.get("Redeemed") and voucher.get("RedemptionDate"):
            return {
                "type": VoucherType.STAMPS.value,
                "target_value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "date_issued": arrow.get(voucher["StartDate"]).timestamp,
                "date_redeemed": arrow.get(voucher["RedemptionDate"]).timestamp,
                "expiry_date": arrow.get(voucher["ExpiryDate"]).timestamp,
            }

        return None

    def _make_cancelled_voucher(self, voucher: Dict) -> [Dict, None]:
        """
        Make a Bink cancelled voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :return: dict of cancelled voucher data mapped for Bink, or None
        """

        if voucher.get("Disabled"):
            return {
                "type": VoucherType.STAMPS.value,
                "target_value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "date_issued": arrow.get(voucher["StartDate"]).timestamp,
                "expiry_date": arrow.get(voucher["ExpiryDate"]).timestamp,
            }

        return None

    def _make_issued_voucher(
        self, voucher: Dict, current_datetime: Arrow
    ) -> [Dict, None]:
        """
        Make a Bink issued voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :param current_datetime: an Arrow datetime obj
        :return: dict of issued voucher data mapped for Bink, or None
        """

        if (
            voucher.get("StartDate")
            and (arrow.get(voucher.get("ExpiryDate")) >= current_datetime)
            and not voucher.get("Redeemed")
            and not voucher.get("Disabled")
        ):
            return {
                "type": VoucherType.STAMPS.value,
                "code": voucher["VoucherCode"],
                "target_value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "date_issued": arrow.get(voucher["StartDate"]).timestamp,
                "expiry_date": arrow.get(voucher["ExpiryDate"]).timestamp,
            }

        return None

    def _make_expired_voucher(
        self, voucher: Dict, current_datetime: Arrow
    ) -> [Dict, None]:
        """
        Make a Bink expired voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :param current_datetime: an Arrow datetime obj
        :return: dict of expired voucher data mapped for Bink, or None
        """

        if arrow.get(voucher.get("ExpiryDate")) < current_datetime:
            return {
                "type": VoucherType.STAMPS.value,
                "target_value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "value": self.POINTS_TARGET_VALUE,  # Should come from Django config
                "date_issued": arrow.get(voucher["StartDate"]).timestamp,
                "expiry_date": arrow.get(voucher["ExpiryDate"]).timestamp,
            }

        return None

    def _make_in_progress_voucher(self, points: Decimal, voucher_type: enum) -> Dict:
        """
        Make an in-progress voucher dict

        :param points: LoyaltyPointsBalance field in the Acteol voucher data
        :return: dict of in-progress voucher data mapped for Bink
        """
        in_progress_voucher = {
            "type": voucher_type.value,
            "target_value": self.POINTS_TARGET_VALUE,  # Should come from Django config
            "value": points,
        }

        return in_progress_voucher

    def _format_money_value(self, money_value: [float, int]) -> str:
        """
        Pad to 2 decimal places
        """
        money_value = f"{money_value:.2f}"

        return money_value

    def _make_transaction_description(
        self, location_name: str, formatted_total_cost: str
    ) -> str:
        """
        e.g. "Kensington High St £6.10"
        """
        description = f"{location_name} £{formatted_total_cost}"

        return description

    def _get_valid_api_token_and_make_headers(self):
        """
        Ensure our Acteol API token is valid and use to create headers for requests
        """
        # Get a valid API token
        token = self.authenticate()
        # Add auth for subsequent API calls
        self.headers = self._make_headers(token=token["acteol_access_token"])


class Wasabi(Acteol):
    ORIGIN_ROOT = "Bink-Wasabi"
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    API_TIMEOUT = 10  # n_seconds until timeout for calls to Acteol's API
    RETAILER_ID = "315"
    POINTS_TARGET_VALUE = 7  # Hardcoded for now, but must come out of Django config
    N_TRANSACTIONS = 5  # Number of transactions to return from Acteol's API
