import json
from typing import Dict

import arrow
import requests
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS, NO_SUCH_RECORD, STATUS_LOGIN_FAILED, STATUS_REGISTRATION_FAILED, UNKNOWN, RegistrationError)
from app.configuration import Configuration
from app.encryption import HashSHA1
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, logger


class Acteol(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        self.token_store = UserTokenStore(REDIS_URL)
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

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

    def authenticate(self) -> None:
        """
        Get an API token from redis if we have one, otherwise login to get one and store in cache.
        This token is not per-user, it is for our backend to use their API
        """
        have_valid_token = False  # Assume no good token to begin with
        current_timestamp = arrow.utcnow().timestamp
        try:
            token = json.loads(self.token_store.get(self.scheme_id))
            try:  # Token may be in bad format and needs refreshing
                if self._token_is_valid(
                    token=token, current_timestamp=current_timestamp
                ):
                    have_valid_token = True
                    self.token = token
            except (KeyError, TypeError) as e:
                logger.exception(e)
        except (KeyError, self.token_store.NoSuchToken):
            pass  # have_token is still False

        if not have_valid_token:
            acteol_access_token = self._refresh_access_token()
            token = self._store_token(
                acteol_access_token=acteol_access_token,
                current_timestamp=current_timestamp,
            )
            self.token = token

    # def register(self, credentials):
    #     consents = {c["slug"]: c["value"] for c in credentials.get("consents", {})}
    #     resp = requests.post(
    #         f"{self.base_url}/v1/list/append_item/{self.RETAILER_ID}/assets/membership",
    #         json={"data": self._get_registration_credentials(credentials, consents)},
    #         headers=self._make_headers(self._authenticate()),
    #     )
    #
    #     if resp.status_code == 409:
    #         raise RegistrationError(ACCOUNT_ALREADY_EXISTS)
    #     else:
    #         resp.raise_for_status()
    #         json = resp.json()
    #         message = json["publisher"][0]["message"]
    #
    #     card_number, uid = self._get_card_number_and_uid(message)
    #
    #     self.identifier = {"card_number": card_number, "merchant_identifier": uid}
    #     self.user_info["credentials"].update(self.identifier)

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

    def register(self, credentials):
        """
        - Generate an OriginID for the user, where OriginID = SHA1(Bink-Wasabi-user_email)
        - Check if account already exists - FindByOriginID
        - Found - “Customer already exists”: Membership Card State=Failed and Reason Code=X202
        - Note: FindByOriginID response will not return a failure - the API will return a non-empty list
        - Not found -continue to step 4
        - Note: The FindByOriginID response will not return a failure - the API will return a empty list
        - All other responses (including 3xx/5xx) are caught and the card ends up in a failed state
        (retry mechanisms are implemented as part of MER-314)
        """
        self.errors = {
            ACCOUNT_ALREADY_EXISTS: "AlreadyExists",
            STATUS_REGISTRATION_FAILED: "Invalid",
            UNKNOWN: "Fail",
        }

        # Get a valid API token
        self.attempt_authenticate()

        origin_id = self._create_origin_id(user_email=credentials.get("email", ""), origin_root=self.ORIGIN_ROOT)
        api_url = f"{self.BASE_API_URL}/api/Contact/FindByOriginID?OriginID={origin_id}"
        self.headers = self._make_headers(token=self.token["token"])
        self.register_response = self.make_request(
            api_url, method="get", timeout=10
        )

        # TODO: check actual message
        message = self.register_response.json()
        if message == "Success":
            return {"message": "success"}

        # TODO: will probably have to overwrite - see AC
        self.handle_errors(message, exception_type=RegistrationError)
