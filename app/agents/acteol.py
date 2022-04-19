import json
from decimal import Decimal
from enum import Enum
from http import HTTPStatus
from typing import Optional
from urllib.parse import urljoin

import arrow
import requests
import sentry_sdk
from blinker import signal
from soteria.configuration import Configuration

import settings
from app.agents.base import BaseAgent
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    END_SITE_DOWN,
    JOIN_ERROR,
    NO_SUCH_RECORD,
    STATUS_LOGIN_FAILED,
    VALIDATION,
    AgentError,
    JoinError,
    LoginError,
)
from app.agents.schemas import Balance, Transaction, Voucher
from app.encryption import HashSHA1
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES
from app.tasks.resend_consents import ConsentStatus, send_consents
from app.vouchers import VoucherState, VoucherType, voucher_state_names

RETRY_LIMIT = 3  # Number of times we should attempt another Acteol API call on failure

log = get_logger("acteol-agent")


class Acteol(BaseAgent):
    ORIGIN_ROOT: str
    N_TRANSACTIONS: int
    API_TIMEOUT: int
    AGENT_CONSENT_TRIES: int
    HERMES_CONFIRMATION_TRIES: int

    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.source_id = "acteol"
        self.config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.credentials = user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.auth = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self.authentication_service = self.config.security_credentials["outbound"]["service"]

    # Public methods

    def get_auth_url_and_payload(self):
        url = urljoin(self.base_url, "token")
        payload = {
            "grant_type": "password",
            "username": self.auth["username"],
            "password": self.auth["password"],
        }
        return url, payload

    def join(self):
        """
        Join a new loyalty scheme member with Acteol. The steps are:
        * Get API token
        * Check if account already exists
        * If not, create account
        * Use the CtcID from create account to add member number in Acteol
        * Get the customer details from Acteol
        * Post user preferences (marketing email opt-in) to Acteol
        * Use the customer details in Bink system
        """
        # Ensure a valid API token
        self.authenticate()
        # Create an origin id for subsequent API calls
        user_email = self.credentials["email"]
        origin_id = self._create_origin_id(user_email=user_email, origin_root=self.ORIGIN_ROOT)

        # These calls may result in various exceptions that mean the join has failed. If so,
        # call the signal event for failure
        try:
            # Check if account already exists
            account_already_exists = self._account_already_exists(origin_id=origin_id)
            if account_already_exists:
                raise JoinError(ACCOUNT_ALREADY_EXISTS)  # The join journey ends

            # The account does not exist, so we can create one
            ctcid = self._create_account(origin_id=origin_id)

            # Add the new member number to Acteol
            member_number = self._add_member_number(ctcid=ctcid)

            # Get customer details
            customer_details = self._get_customer_details(origin_id=origin_id)
            if not self._customer_fields_are_present(customer_details=customer_details):
                log.debug(
                    (
                        "Expected fields not found in customer details during join: Email, "
                        f"CurrentMemberNumber, CustomerID for user email: {user_email}"
                    )
                )
                raise JoinError(JOIN_ERROR)
        except (AgentError, LoginError, JoinError):
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise
        else:
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)

        # Set user's email opt-in preferences in Acteol, if opt-in is True
        consents = self.credentials.get("consents", [{}])
        email_optin = self._get_email_optin_from_consent(consents=consents)
        if email_optin:
            self._set_customer_preferences(ctcid=ctcid, email_optin=email_optin)
        else:
            self.consent_confirmation(consents_data=consents, status=ConsentStatus.NOT_SENT)

        # Set up instance attributes that will result in the creation of an active membership card
        self.identifier = {
            "card_number": member_number,
            "merchant_identifier": ctcid,
        }
        self.user_info["credentials"].update(self.identifier)

    def balance(self) -> Optional[Balance]:
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
        self.authenticate()
        # Create an origin id for subsequent API calls, using credentials created during instantiation
        user_email = self.credentials["email"]
        origin_id = self._create_origin_id(user_email=user_email, origin_root=self.ORIGIN_ROOT)

        try:
            # Get customer details
            customer_details = self._get_customer_details(origin_id=origin_id)
        except AgentError as ex:
            sentry_issue_id = sentry_sdk.capture_exception(ex)
            log.error(
                f"Balance Error: {ex.message}, Sentry Issue ID: {sentry_issue_id}, Scheme: {self.scheme_slug} "
                f"Scheme Account ID: {self.scheme_id}"
            )
            return None

        if not self._customer_fields_are_present(customer_details=customer_details):
            log.debug(
                (
                    "Expected fields not found in customer details during join: Email, CurrentMemberNumber, CustomerID "
                    f"for user email: {user_email}"
                )
            )
            raise AgentError(NO_SUCH_RECORD)

        self._check_deleted_user(resp_json=customer_details)
        points = Decimal(customer_details["LoyaltyPointsBalance"])

        # Make sure we have a populated merchant_identifier in credentials. This is required to get voucher
        # data from Acteol. Wasabi user’s credentials to be updated if they are updated within Acteol,
        # so that the user’s scheme account reflects the correct data.
        self.credentials["merchant_identifier"] = customer_details["CustomerID"]
        ctcid = self.credentials["merchant_identifier"]

        self.update_hermes_credentials(ctcid, customer_details)

        # Get all vouchers for this customer
        vouchers = self._get_vouchers(ctcid=ctcid)

        # Filter for BINK only vouchers
        bink_only_vouchers = self._filter_bink_vouchers(vouchers=vouchers)
        bink_mapped_vouchers = []  # Vouchers mapped to format required by Bink

        # Create an 'in-progress' voucher - the current, incomplete voucher
        in_progress_voucher = self._make_in_progress_voucher(points=points, voucher_type=VoucherType.STAMPS)
        bink_mapped_vouchers.append(in_progress_voucher)

        # Now create the other types of vouchers
        for bink_only_voucher in bink_only_vouchers:
            if bink_mapped_voucher := self._map_acteol_voucher_to_bink_struct(voucher=bink_only_voucher):
                bink_mapped_vouchers.append(bink_mapped_voucher)

        return Balance(
            points=points,
            value=points,
            value_label="",
            vouchers=bink_mapped_vouchers,
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            log.warning(f"{self} failed to get transactions: {repr(ex)}")
            return []

    def update_hermes_credentials(self, ctcid, customer_details):
        # GIVEN user has Wasabi card with given ‘card number’ and 'CTCID'
        # WHEN the corresponding Acteol field is updated i.e CurrentMemberNumber and CustomerID
        self.credentials["card_number"] = customer_details["CurrentMemberNumber"]
        card_number = self.credentials["card_number"]

        self.identifier = {
            "card_number": card_number,
            "merchant_identifier": ctcid,
        }
        self.user_info["credentials"].update(self.identifier)

        scheme_account_id = self.user_info["scheme_account_id"]
        # for updating user ID credential you get for joining (e.g. getting issued a card number)
        api_url = urljoin(
            settings.HERMES_URL,
            f"schemes/accounts/{scheme_account_id}/credentials",
        )
        headers = {
            "Content-type": "application/json",
            "Authorization": "token " + settings.SERVICE_API_KEY,
        }
        requests.put(  # Don't want to call any signals for internal calls
            api_url, data=self.identifier, headers=headers, timeout=self.API_TIMEOUT
        )

    def parse_transaction(self, transaction: dict) -> Transaction:
        """
        Convert an individual transaction record from Acteol's system to the format expected by Bink

        :param transaction: a transaction record
        :return: transaction record in the format required by Bink
        """
        formatted_total_cost = self._format_money_value(money_value=transaction["TotalCost"])

        return Transaction(
            date=arrow.get(transaction["OrderDate"]),
            description=self._make_transaction_description(
                location_name=transaction["LocationName"],
                formatted_total_cost=formatted_total_cost,
            ),
            points=self._decimalise_to_two_places(transaction["PointEarned"]),
            location=transaction["LocationName"],
        )

    def transaction_history(self) -> list[Transaction]:
        """
        Call the Acteol API to retrieve transaction history

        :return: list of transactions from Acteol's API
        """
        # Ensure a valid API token
        self.authenticate()

        ctcid: str = self.credentials["merchant_identifier"]
        api_url = urljoin(
            self.base_url,
            f"api/Order/Get?CtcID={ctcid}&LastRecordsCount={self.N_TRANSACTIONS}&IncludeOrderDetails=false",
        )
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        resp_json = resp.json()

        # The API can return a dict if there's an error but a list normally returned.
        if isinstance(resp_json, dict):
            error_msg = resp_json.get("Error")
            if error_msg:
                sentry_issue_id = sentry_sdk.capture_exception()
                log.error(
                    f"Scrape Transaction Error: {error_msg},Sentry Issue ID: {sentry_issue_id}"
                    f"Scheme: {self.scheme_slug} ,Scheme Account ID: {self.scheme_id}"
                )
                return []

        transactions = [self.parse_transaction(tx) for tx in resp_json]

        return transactions

    def get_contact_ids_by_email(self, email: str) -> dict:
        """
        Get dict of contact ids from Acteol by email

        :param email: user's email address
        """
        # Ensure a valid API token
        self.authenticate()

        api_url = urljoin(self.base_url, f"api/Contact/GetContactIDsByEmail?Email={email}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        resp.raise_for_status()
        resp_json = resp.json()
        self._check_response_for_error(resp_json)

        return resp_json

    def delete_contact_by_ctcid(self, ctcid: str):
        """
        Delete a customer by their CtcID (aka CustomerID)
        """
        # Ensure a valid API token
        self.authenticate()

        api_url = urljoin(self.base_url, f"api/Contact/DeleteContact/{ctcid}")
        resp = self.make_request(api_url, method="delete", timeout=self.API_TIMEOUT)

        return resp

    def login(self) -> None:
        """
        Acteol works slightly differently to some other agents, as we must authenticate() before each call to
        ensure our API token is still valid / not expired. See authenticate()
        """
        # If we are on an add journey, then we will need to verify the supplied email against the card number.
        # Being on an add journey is defined as having a card number but no "from_join" field, and we
        # won't have a "merchant_identifier" (which would indicate a balance request instead).
        if (
            self.credentials["card_number"]
            and not self.user_info.get("from_join")
            and not self.credentials.get("merchant_identifier")
        ):
            try:
                ctcid = self._validate_member_number(self.credentials)
                signal("log-in-success").send(self, slug=self.scheme_slug)
                self.identifier_type = [
                    "card_number",  # Not sure this is needed but the base class has one
                ]
                # Set up attributes needed for the creation of an active membership card
                self.identifier = {
                    "card_number": self.credentials["card_number"],
                    "merchant_identifier": ctcid,
                }
                self.user_info["credentials"].update({"merchant_identifier": ctcid})
            except (AgentError, LoginError):
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                raise

        return

    def _get_customer_details(self, origin_id: str) -> dict:
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
            log.debug(f"Error while fetching customer details, reason: {resp.status_code} {resp.reason}")
            raise JoinError(JOIN_ERROR)  # The join journey ends

        resp_json = resp.json()
        self._check_response_for_error(resp_json)

        return resp_json

    def _account_already_exists(self, origin_id: str) -> bool:
        """
        Check if account already exists in Acteol

        FindByOriginID will return HTTPStatus.OK and an empty list if the account does NOT exist.
        It will return HTTPStatus.OK and details in the json if the account exists.
        All other responses (including 3xx/5xx) should be caught and the card ends up in a failed state

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        """
        api_url = urljoin(self.base_url, f"api/Contact/FindByOriginID?OriginID={origin_id}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)

        if resp.status_code != HTTPStatus.OK:
            log.debug(f"Error while checking for existing account, reason: {resp.status_code} {resp.reason}")
            raise JoinError(JOIN_ERROR)  # The join journey ends

        # The API can return a dict if there's an error but a list normally returned.
        resp_json = resp.json()
        if isinstance(resp_json, dict):
            self._check_response_for_error(resp_json)

        if resp_json:
            return True

        return False

    def _create_account(self, origin_id: str) -> str:
        """
        Create an account in Acteol

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        :param credentials: dict of user's credentials
        """
        api_url = urljoin(self.base_url, "api/Contact/PostContact")
        payload = {
            "OriginID": origin_id,
            "SourceID": "BinkPlatform",
            "FirstName": self.credentials["first_name"],
            "LastName": self.credentials["last_name"],
            "Email": self.credentials["email"],
            "BirthDate": self.credentials["date_of_birth"],
            "SupInfo": [{"FieldName": "BINK", "FieldContent": "True"}],
        }
        resp = self.make_request(api_url, method="post", timeout=self.API_TIMEOUT, audit=True, json=payload)
        resp_json = resp.json()
        self._check_response_for_error(resp_json)

        if resp.status_code != HTTPStatus.OK:
            log.debug(f"Error while creating new account, reason: {resp.status_code} {resp.reason}")
            raise JoinError(JOIN_ERROR)  # The join journey ends

        ctcid = resp_json["CtcID"]

        return ctcid

    def _add_member_number(self, ctcid: str) -> str:
        """
        Add member number to Acteol

        :param ctcid: ID returned from Acteol when creating the account
        """
        api_url = urljoin(self.base_url, f"api/Contact/AddMemberNumber?CtcID={ctcid}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT, audit=True)
        if resp.status_code != HTTPStatus.OK:
            log.debug(f"Error while adding member number, reason: {resp.status_code} {resp.reason}")
            raise JoinError(JOIN_ERROR)  # The join journey ends

        resp_json = resp.json()
        self._check_response_for_error(resp_json)

        member_number = resp_json["MemberNumber"]

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

    def _customer_fields_are_present(self, customer_details: dict) -> bool:
        """
        These fields are required and expected, so it's an exception if they're not there
        """
        return all([k in customer_details for k in ["Email", "CurrentMemberNumber", "CustomerID"]])

    def _set_customer_preferences(self, ctcid: str, email_optin: dict):
        """
        Set user's email opt-in preferences in Acteol, retry on fail up to retry limit and then
        update Hermes with the results.

        :param email_optin: dict of email optin consent
        """
        api_url = urljoin(self.base_url, "api/CommunicationPreference/Post")
        # Add content type etc into header that already contains the auth info
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        headers.update(self.headers)
        payload = {
            "CustomerID": ctcid,
            "EmailOptin": email_optin["value"],
        }
        # Will hold the retry count down for each consent confirmation retried
        confirm_retries = {email_optin["id"]: self.HERMES_CONFIRMATION_TRIES}

        send_consents(
            {
                "url": api_url,  # set to scheme url for the agent to accept consents
                "headers": headers,  # headers used for agent consent call
                "message": json.dumps(payload),  # set to message body encoded as required
                "agent_tries": self.AGENT_CONSENT_TRIES,  # max number of attempts to send consents to agent
                "confirm_tries": confirm_retries,  # retries for each consent confirmation sent to hermes
                "id": ctcid,  # used for identification in error messages
                "callback": "app.agents.acteol"  # If present identifies the module containing the
                # function "agent_consent_response"
                # callback_function can be set to change default function
                # name.  Without this the HTML repsonse status code is used
            }
        )

    def _get_email_optin_from_consent(self, consents: list[dict]) -> dict:
        """
        Find the dict (should only be one, so return the first one found) with a key of EmailOptin that also has a
        key of "value" set to True

        :param consents: the list of consents dicts from the user's credentials
        :return: matched consent dict
        """
        matching_true_consents = list(
            filter(
                lambda x: x.get("slug") == "EmailOptin" and bool(x.get("value")),
                consents,
            )
        )

        if matching_true_consents:
            return matching_true_consents[0]
        else:
            return {}

    def _validate_member_number(self) -> str:
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
        self.authenticate()

        api_url = urljoin(self.base_url, "api/Contact/ValidateContactMemberNumber")
        member_number = self.credentials["card_number"]
        payload = {
            "MemberNumber": member_number,
            "Email": self.credentials["email"],
        }

        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT, audit=True, json=payload)

        # It's possible for a 200 OK response to be returned, but validation has failed. Get the cause for logging.
        resp_json = resp.json()
        self._check_response_for_error(resp_json)
        validation_msg = resp_json.get("ValidationMsg")
        is_valid = resp_json.get("IsValid")
        if not is_valid:
            validation_error_types = {
                "Invalid Email": VALIDATION,
                "Invalid Member Number": VALIDATION,
                "Email and Member number mismatch": STATUS_LOGIN_FAILED,
            }

            error_type = validation_error_types.get(validation_msg, STATUS_LOGIN_FAILED)
            log.error(f"Failed login validation for member number {member_number}: {validation_msg}")
            raise LoginError(error_type)

        ctcid = str(resp_json["CtcID"])

        return ctcid

    def _get_vouchers(self, ctcid: str) -> list[dict]:
        """
        Get all vouchers for a CustomerID (aka CtcID) from Acteol

        :param ctcid: CustomerID in Acteol and merchant_identifier in Bink
        :return: list of vouchers
        """
        # Ensure a valid API token
        self.authenticate()

        api_url = urljoin(self.base_url, f"api/Voucher/GetAllByCustomerID?customerid={ctcid}")
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        resp_json = resp.json()

        # The API can return a list if there's an error.
        self._check_voucher_response_for_errors(resp_json)

        vouchers = resp_json["voucher"]

        return vouchers

    def _filter_bink_vouchers(self, vouchers: list[dict]) -> list[dict]:
        """
        Filter for BINK only vouchers

        :param vouchers: list of voucher dicts from Acteol
        :return: only those voucher dicts whose CategoryName == "BINK"
        """
        bink_only_vouchers = [voucher for voucher in vouchers if voucher["CategoryName"] == "BINK"]

        return bink_only_vouchers

    def _map_acteol_voucher_to_bink_struct(self, voucher: dict) -> Optional[Voucher]:
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
        bink_voucher = self._make_issued_voucher(voucher=voucher, current_datetime=current_datetime)
        if bink_voucher:
            return bink_voucher
        # Is it expired?
        bink_voucher = self._make_expired_voucher(voucher=voucher, current_datetime=current_datetime)
        if bink_voucher:
            return bink_voucher

        log.warning(
            f'Acteol voucher did not match any of the Bink structure criteria, voucher id: {voucher["VoucherID"]}'
        )

        return None

    def _make_redeemed_voucher(self, voucher: dict) -> Optional[Voucher]:
        """
        Make a Bink redeemed voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :return: dict of redeemed voucher data mapped for Bink, or None
        """

        if voucher.get("Redeemed") and voucher.get("RedemptionDate"):
            return Voucher(
                state=voucher_state_names[VoucherState.REDEEMED],
                type=VoucherType.STAMPS.value,
                code=voucher.get("VoucherCode"),
                target_value=None,  # None == will be set to Earn Target Value in Hermes
                value=None,  # None == will be set to Earn Target Value in Hermes
                issue_date=arrow.get(voucher["URD"]).int_timestamp,
                redeem_date=arrow.get(voucher["RedemptionDate"]).int_timestamp,
                expiry_date=arrow.get(voucher["ExpiryDate"]).int_timestamp,
            )

        return None

    def _make_cancelled_voucher(self, voucher: dict) -> Optional[Voucher]:
        """
        Make a Bink cancelled voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :return: dict of cancelled voucher data mapped for Bink, or None
        """

        if voucher.get("Disabled"):
            return Voucher(
                state=voucher_state_names[VoucherState.CANCELLED],
                type=VoucherType.STAMPS.value,
                code=voucher.get("VoucherCode"),
                target_value=None,  # None == will be set to Earn Target Value in Hermes
                value=None,  # None == will be set to Earn Target Value in Hermes
                issue_date=arrow.get(voucher["URD"]).int_timestamp,
                expiry_date=arrow.get(voucher["ExpiryDate"]).int_timestamp,
            )

        return None

    def _make_issued_voucher(self, voucher: dict, current_datetime: arrow.Arrow) -> Optional[Voucher]:
        """
        Make a Bink issued voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :param current_datetime: an Arrow datetime obj
        :return: dict of issued voucher data mapped for Bink, or None
        """

        expiry: Optional[str] = voucher.get("ExpiryDate")
        if (
            voucher.get("URD")
            and expiry
            and (arrow.get(expiry) >= current_datetime)
            and not voucher.get("Redeemed")
            and not voucher.get("Disabled")
        ):
            return Voucher(
                state=voucher_state_names[VoucherState.ISSUED],
                type=VoucherType.STAMPS.value,
                code=voucher["VoucherCode"],
                target_value=None,  # None == will be set to Earn Target Value in Hermes
                value=None,  # None == will be set to Earn Target Value in Hermes
                issue_date=arrow.get(voucher["URD"]).int_timestamp,
                expiry_date=arrow.get(voucher["ExpiryDate"]).int_timestamp,
            )

        return None

    def _make_expired_voucher(self, voucher: dict, current_datetime: arrow.Arrow) -> Optional[Voucher]:
        """
        Make a Bink expired voucher dict if the Acteol voucher is of that type

        :param voucher: dict of a single voucher's data from Acteol
        :param current_datetime: an Arrow datetime obj
        :return: dict of expired voucher data mapped for Bink, or None
        """

        expiry: Optional[str] = voucher.get("ExpiryDate")
        if expiry and arrow.get(expiry) < current_datetime:
            return Voucher(
                state=voucher_state_names[VoucherState.EXPIRED],
                type=VoucherType.STAMPS.value,
                code=voucher.get("VoucherCode"),
                target_value=None,  # None == will be set to Earn Target Value in Hermes
                value=None,  # None == will be set to Earn Target Value in Hermes
                issue_date=arrow.get(voucher["URD"]).int_timestamp,
                expiry_date=arrow.get(voucher["ExpiryDate"]).int_timestamp,
            )

        return None

    def _make_in_progress_voucher(self, points: Decimal, voucher_type: Enum) -> Voucher:
        """
        Make an in-progress voucher dict

        :param points: LoyaltyPointsBalance field in the Acteol voucher data
        :return: dict of in-progress voucher data mapped for Bink
        """
        return Voucher(
            state=voucher_state_names[VoucherState.IN_PROGRESS],
            type=voucher_type.value,
            target_value=None,  # None == will be set to Earn Target Value in Hermes
            value=points,
        )

    def _format_money_value(self, money_value: str) -> str:
        """
        Pad to 2 decimal places and stringify
        """
        return str(self._decimalise_to_two_places(value=money_value))

    def _decimalise_to_two_places(self, value: str) -> Decimal:
        """
        Round to 2 dp e.g. 7.899 -> 7.90 as Decimal
        """
        decimalised = Decimal(value).quantize(TWO_PLACES)

        return decimalised

    def _make_transaction_description(self, location_name: str, formatted_total_cost: str) -> str:
        """
        e.g. "Kensington High St £6.10"
        """
        description = f"{location_name} £{formatted_total_cost}"

        return description

    def _check_response_for_error(self, resp_json: dict):
        """
        Handle response error
        """
        error_msg = resp_json.get("Error")

        if error_msg:
            log.error(f"End Site Down Error: {error_msg}")
            raise AgentError(END_SITE_DOWN)

    def _check_voucher_response_for_errors(self, resp_json: dict):
        """
        Handle voucher response errors
        """
        error_list = resp_json.get("errors")

        if error_list:
            sentry_issue_id = sentry_sdk.capture_exception()
            log.error(
                f"Voucher Error: {str(error_list)},Sentry Issue ID: {sentry_issue_id}, Scheme: {self.scheme_slug} "
                f"Scheme Account ID: {self.scheme_id}"
            )
            return

    def _check_deleted_user(self, resp_json: dict):
        # When calling a GET Balance set of calls and the response is successful
        # BUT the CustomerID = “0”then this is how Acteol return a deleted account
        card_number = str(resp_json["CurrentMemberNumber"])
        if "CustomerID" in resp_json:
            customer_id = str(resp_json["CustomerID"])
        elif "CtcID" in resp_json:
            customer_id = str(resp_json["CtcID"])

        if customer_id == "0":
            log.error(f"Acteol card number has been deleted: Card number: {card_number}")
            raise AgentError(NO_SUCH_RECORD)


def agent_consent_response(resp):
    """
    Callback to calculate correct response from Acteol's endpoint, as can't rely on status code
    """
    response_data = json.loads(resp.text)
    if response_data.get("Response") and not response_data.get("Error"):
        return True, ""
    return (
        False,
        f'Acteol returned {response_data.get("Error", "")}, Response:{response_data.get("Response", "")}',
    )


class Wasabi(Acteol):
    ORIGIN_ROOT = "Bink-Wasabi"
    API_TIMEOUT = 10  # n_seconds until timeout for calls to Acteol's API
    RETAILER_ID = "315"
    N_TRANSACTIONS = 5  # Number of transactions to return from Acteol's API
    # Number of attempts to send consents to Agent must be > 0
    # (0 = no send , 1 send once, 2 = 1 retry)
    AGENT_CONSENT_TRIES = 10
    # no of attempts to confirm to hermes Agent has received consents
    HERMES_CONFIRMATION_TRIES = 10

    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.auth_token_timeout = 75600  # n_seconds in 21 hours
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
