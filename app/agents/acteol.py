import json
from decimal import Decimal
from http import HTTPStatus
from typing import Dict, List

import arrow
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    JOIN_ERROR,
    NO_SUCH_RECORD,
    AgentError,
    RegistrationError,
)
from app.configuration import Configuration
from app.encryption import HashSHA1
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, logger
from tenacity import retry, stop_after_attempt, wait_exponential

RETRY_LIMIT = 3  # Number of times we should attempt another Acteol API call on failure


class Acteol(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.credentials = user_info["credentials"]
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        self.token_store = UserTokenStore(REDIS_URL)
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

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
            token = json.loads(self.token_store.get(self.scheme_id))
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

    def register(self, credentials):
        """
        Register a new loyalty scheme member with Acteol. The steps are:
        - Get API token
        - Check if account already exists
        - If not, create account
        - Use the CtcID from create account to add member number in Acteol
        - Get the customer details from Acteol
        - Post user preferences (marketing email opt-in) to Acteol
        - Use the customer details in Bink system
        """
        # Get a valid API token
        token = self.authenticate()
        # Add auth for subsequent API calls
        self.headers = self._make_headers(token=token["token"])
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
        Get the balance from the Acteol API, return the expected format
        """
        # Get a valid API token
        token = self.authenticate()
        # Add auth for subsequent API calls
        self.headers = self._make_headers(token=token["token"])
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

        return {
            "points": points,
            "value": points,
            "value_label": "",
        }

    @staticmethod
    def parse_transaction(row):
        """
        Required to be implemented by the base class
        """
        return row

    def scrape_transactions(self):
        """
        The resources endpoints/methods expect some implementation of scrape_transactions()
        """
        return []

    def get_contact_ids_by_email(self, email: str) -> Dict:
        """
        Get dict of contact ids from Acteol by email
        :param email: user's email address
        """
        # Get a valid API token
        token = self.authenticate()
        # Add auth
        self.headers = self._make_headers(token=token["token"])

        api_url = f"{self.BASE_API_URL}/Contact/GetContactIDsByEmail?Email={email}"
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)
        resp.raise_for_status()
        contact_ids_data = resp.json()

        return contact_ids_data

    def delete_contact_by_ctcid(self, ctcid: str):
        # Get a valid API token
        token = self.authenticate()
        # Add auth
        self.headers = self._make_headers(token=token["token"])
        api_url = f"{self.BASE_API_URL}/Contact/DeleteContact/{ctcid}"
        resp = self.make_request(api_url, method="delete", timeout=self.API_TIMEOUT)

        return resp

    def login(self, credentials) -> None:
        """
        Acteol works slightly differently to some other agents, as we must authenticate() before each call to
        ensure our API token is still valid / not expired. See authenticate()
        """
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
        api_url = (
            f"{self.BASE_API_URL}/Loyalty/GetCustomerDetailsByExternalCustomerID"
            f"?externalcustomerid={origin_id}&partnerid=BinkPlatform"
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
        api_url = f"{self.BASE_API_URL}/Contact/FindByOriginID?OriginID={origin_id}"
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
        api_url = f"{self.BASE_API_URL}/Contact/PostContact"
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
        api_url = f"{self.BASE_API_URL}/Contact/AddMemberNumber?CtcID={ctcid}"
        resp = self.make_request(api_url, method="get", timeout=self.API_TIMEOUT)

        if resp.status_code != HTTPStatus.OK:
            logger.debug(f"Error while adding member number, reason: {resp.reason}")
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        member_number = resp.json().get("MemberNumber")

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
        token_url = f"{self.base_url}/token"
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
        token = {"token": acteol_access_token, "timestamp": current_timestamp}
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
        Condition: “EmailOptin” = true if Enrol user consent has been marked as true.
        :param email_optin_pref: boolean
        """
        api_url = f"{self.BASE_API_URL}/CommunicationPreference/Post"
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


class Wasabi(Acteol):
    BASE_API_URL = "https://wasabiuat.wasabiworld.co.uk/api"
    ORIGIN_ROOT = "Bink-Wasabi"
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    API_TIMEOUT = 10  # n_seconds until timeout for calls to Acteol's API
    RETAILER_ID = "315"
    POINTS_TARGET_VALUE = 7  # Hardcoded for now, but must come out of Django config
