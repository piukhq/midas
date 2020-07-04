import json
from decimal import Decimal
from typing import Dict

import arrow
import requests
from app.agents.base import ApiMiner
from app.agents.exceptions import ACCOUNT_ALREADY_EXISTS, JOIN_ERROR, RegistrationError
from app.configuration import Configuration
from app.encryption import HashSHA1
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, logger


class JoinJourney:
    def account_already_exists(self, origin_id: str) -> bool:
        """
        Check if account already exists in Acteol

        FindByOriginID will return 200 and an empty list if the account does NOT exist.
        It will return 200 and details in the json if the account exists.
        All other responses (including 3xx/5xx) should be caught and the card ends up in a failed state

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        """
        api_url = f"{self.BASE_API_URL}/Contact/FindByOriginID?OriginID={origin_id}"
        register_response = self.make_request(api_url, method="get", timeout=10)

        # TODO: raise on 3**/4**/5** errors but will implement retries as part of ticket MER-314
        if register_response.status_code != 200:
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        response_json = register_response.json()
        if register_response.status_code == 200 and response_json:
            return True

        return False

    def create_account(self, origin_id: str, credentials: Dict) -> str:
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
        register_response = self.make_request(
            api_url, method="post", timeout=10, json=payload
        )

        # TODO: raise on 3**/4**/5** errors but will implement retries as part of ticket MER-314
        if register_response.status_code != 200:
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        response_json = register_response.json()
        ctcid = response_json["CtcID"]

        return ctcid

    def add_member_number(self, ctcid: str) -> str:
        """
        Add member number to Acteol

        :param ctcid: ID returned from Acteol when creating the account
        """
        api_url = f"{self.BASE_API_URL}/Contact/AddMemberNumber?CtcID={ctcid}"
        add_member_response = self.make_request(api_url, method="get", timeout=10)

        # TODO: raise on 3**/4**/5** errors but will implement retries as part of ticket MER-314
        if add_member_response.status_code != 200:
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        member_number = add_member_response.json().get("MemberNumber")

        return member_number


class Acteol(JoinJourney, ApiMiner):
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

    def get_customer_details(self, origin_id: str) -> Dict:
        """
        Get the customer details from Acteol

        :param origin_id: hex string of encrypted credentials, standard ID for company plus email
        """
        api_url = (f"{self.BASE_API_URL}/Loyalty/GetCustomerDetailsByExternalCustomerID"
                   f"?externalcustomerid={origin_id}&partnerid=BinkPlatform")
        customer_details_response = self.make_request(api_url, method="get", timeout=10)

        # TODO: raise on 3**/4**/5** errors but will implement retries as part of ticket MER-314
        if customer_details_response.status_code != 200:
            raise RegistrationError(JOIN_ERROR)  # The join journey ends

        customer_details_data = customer_details_response.json()

        return customer_details_data

    def register(self, credentials):
        """
        Register a new loyalty scheme member with Acteol. The steps are:
        - Get API token
        - Check if account already exists
        - If not, create account
        - Use the CtcID from create account to add member number in Acteol
        - Get the customer details from Acteol
        - Use the customer details in Bink system
        (retry mechanisms are implemented as part of MER-314)
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
        account_already_exists = self.account_already_exists(origin_id=origin_id)
        if account_already_exists:
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)  # The join journey ends

        # The account does not exist, so we can create one
        ctcid = self.create_account(origin_id=origin_id, credentials=credentials)
        assert ctcid

        # Add the new member number to Acteol
        member_number = self.add_member_number(ctcid=ctcid)
        # Sanity check: there must be a member_number
        assert member_number

        # Get customer details
        customer_details = self.get_customer_details(origin_id=origin_id)
        # Must at least have these or something is un-recoverably wrong
        assert customer_details["Email"]
        assert customer_details[
            "CurrentMemberNumber"
        ]  # This is the same as member_number, from above
        assert customer_details["CustomerID"]  # This is the same as ctcid, from above

        # Set up instance attributes that will result in the creation of an active membership card
        # from the customer details response
        # - Generate an “inprogress” voucher
        # - Current Stamps => LoyaltyPointsBalance
        # - Stamp Goal => will need to be pulled from the Plan Configuration
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
        customer_details = self.get_customer_details(origin_id=origin_id)
        # Must at least have these or something is un-recoverably wrong
        assert customer_details["Email"]
        assert customer_details[
            "CurrentMemberNumber"
        ]  # This is the same as member_number, from above
        assert customer_details["CustomerID"]  # This is the same as ctcid, from above

        # TODO: target value must eventually come from Django config
        value = Decimal(customer_details["LoyaltyPointsBalance"] / self.TARGET_VALUE)
        current_timestamp = arrow.utcnow().timestamp

        return {
            "value": value,
            "currency": "stamps",
            "suffix": "stamps",
            "updated_at": current_timestamp,
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
        contact_ids_response = self.make_request(api_url, method="get", timeout=10)
        contact_ids_response.raise_for_status()
        contact_ids_data = contact_ids_response.json()

        return contact_ids_data

    def delete_contact_by_ctcid(self, ctcid: str):
        # Get a valid API token
        token = self.authenticate()
        # Add auth
        self.headers = self._make_headers(token=token["token"])
        api_url = f"{self.BASE_API_URL}/Contact/DeleteContact/{ctcid}"
        delete_response = self.make_request(api_url, method="delete", timeout=10)

        return delete_response

    def login(self, credentials) -> None:
        """
        Acteol works slightly differently to some other agents, as we must authenticate() before each call to
        ensure our API token is still valid / not expired. See authenticate()
        """
        self.credentials = (
            credentials  # Ensure credentials are available via the instance
        )

        return

    # Private methods
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
        resp = requests.post(token_url, data=payload)
        resp.raise_for_status()
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


class Wasabi(Acteol):
    BASE_API_URL = "https://wasabiuat.wasabiworld.co.uk/api"
    ORIGIN_ROOT = "Bink-Wasabi"
    AUTH_TOKEN_TIMEOUT = 75600  # n_seconds in 21 hours
    RETAILER_ID = "315"
    TARGET_VALUE = 7  # Hardcoded for now, but must come out of Django config
