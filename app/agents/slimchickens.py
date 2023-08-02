import base64
from http import HTTPStatus
from typing import Any

from blinker import signal
from soteria.configuration import Configuration

import settings
from app.agents.base import BaseAgent
from app.exceptions import BaseError, ConfigurationError
from app.reporting import get_logger

RETRY_LIMIT = 3
log = get_logger("slim-chickens")


class SlimChickens(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.integration_service = "SYNC"
        self.credentials = self.user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.username = settings.SLIM_CHICKENS_USERNAME
        self.password = settings.SLIM_CHICKENS_PASSWORD
        self.channel_key = settings.SLIM_CHICKENS_CHANNEL_KEY
        self.account_key = settings.SLIM_CHICKENS_ACCOUNT_KEY

    def _authenticate(self):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        else:
            try:
                auth_credentials = f"{self.username}:{self.password}"
                auth_header_value = base64.b64encode(auth_credentials.encode()).decode()
                self.headers["Authorization"] = f"Basic {auth_header_value}"
            except (KeyError, TypeError) as e:
                raise ConfigurationError(exception=e) from e

    def _verify_user_account(self) -> bool:
        self._authenticate()
        payload = {
            "username": self.credentials["email"],
            "channels": [{"channelKey": self.channel_key}],
        }
        resp = self.make_request(self.url, method="post", audit=True, json=payload)
        if resp.status_code == HTTPStatus.OK:
            raise Exception("Error account already exists")
        elif resp.status_code == HTTPStatus.CONFLICT:
            return False
        else:
            log.debug(f"Error while checking if user exists, reason: {resp.status_code} {resp.reason}")
            raise Exception("Error while checking if user exists")

    def join(self) -> Any:
        self.url = f"{self.base_url}core/account/{self.account_key}/consumer"
        if not self._verify_user_account():
            payload = {
                "firstName": self.credentials["first_name"],
                "lastName": self.credentials["last_name"],
                "username": self.credentials["email"],
                "password": self.credentials["password"],
                "dob": self.credentials["date_of_birth"],
                "attributes": {"optin2": self.credentials["marketing_consent"]},
                "channels": [{"channelKey": self.channel_key}],
            }
            try:
                resp = self.make_request(self.url, method="post", audit=True, json=payload)
                signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
            except BaseError as ex:
                print(ex)
                signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
        response_data = resp.json()
        self.identifier = {
            "merchant_identifier": response_data["consumer"]["email"],
        }
        self.credentials.update(self.identifier)
