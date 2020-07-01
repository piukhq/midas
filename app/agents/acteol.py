import json
from typing import Dict

import arrow
import requests
from app.agents.base import ApiMiner
from app.configuration import Configuration
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

    def _refresh_access_token(self, credentials: Dict) -> str:
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
        self.token_store.set(self.scheme_id, json.dumps(token))

        return token

    def login(self, credentials: Dict) -> None:
        """
        get token from redis if we have one, otherwise login to get one and store in cache
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
            acteol_access_token = self._refresh_access_token(credentials=credentials)
            token = self._store_token(
                acteol_access_token=acteol_access_token,
                current_timestamp=current_timestamp,
            )
            self.token = token
