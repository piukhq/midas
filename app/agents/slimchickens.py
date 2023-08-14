import base64
from http import HTTPStatus
from typing import Any, Optional
from urllib.parse import urljoin

from blinker import signal
from soteria.configuration import Configuration
from app.agents.schemas import Balance

import settings
from app.agents.base import BaseAgent
from app.exceptions import AccountAlreadyExistsError, BaseError, ConfigurationError, WeakPassword
from app.reporting import get_logger

RETRY_LIMIT = 3
log = get_logger("slim-chickens")


class SlimChickens(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.integration_service = "SYNC"
        self.credentials = self.user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.outbound_security = self.config.security_credentials["outbound"]["credentials"][0]["value"]

    def _authenticate(self):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        else:
            try:
                auth_credentials = f"{self.outbound_security['username']}:{self.outbound_security['password']}"
                auth_header_value = base64.b64encode(auth_credentials.encode()).decode()
                self.headers["Authorization"] = f"Basic {auth_header_value}"
            except (KeyError, TypeError) as e:
                raise ConfigurationError(exception=e) from e

    def _verify_new_user_account(self) -> True:
        self._authenticate()
        payload = {
            "username": self.credentials["email"],
            "channels": [{"channelKey": self.outbound_security["channel_key"]}],
        }
        resp = self.make_request(self.url, method="post", audit=True, json=payload)
        if resp.status_code == HTTPStatus.OK:
            raise AccountAlreadyExistsError()  # The join journey ends
        elif "Password is required" in resp.text:
            return True
        else:
            log.debug(f"Error while checking if user exists, reason: {resp.status_code} {resp.reason}")
            raise Exception("Error while checking if user exists")

    def login(self) -> None:
        pass

    def balance(self) -> Optional[Balance]:
        resp = self.make_request(
            urljoin(self.base_url, "/search"),
            json={"channelKeys": [self.outbound_security["channel_key"]], "types": ["wallet"]},
        )

        return Balance()

    def join(self) -> Any:
        self.url = urljoin(self.base_url, f"core/account/{self.outbound_security['account_key']}/consumer")
        if self._verify_new_user_account():
            payload = {
                "firstName": self.credentials["first_name"],
                "lastName": self.credentials["last_name"],
                "username": self.credentials["email"],
                "password": self.credentials["password"],
                "dob": self.credentials["date_of_birth"],
                "attributes": {"optin2": self.credentials.get("consents", [])},
                "channels": [{"channelKey": self.outbound_security["username"]}],
            }
            try:
                resp = self.make_request(self.url, method="post", audit=True, json=payload)
                signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
            except BaseError:
                signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
                if "Password is too weak" in resp.text:
                    raise WeakPassword()
                else:
                    raise

        response_data = resp.json()
        self.identifier = {
            "merchant_identifier": response_data["consumer"]["email"],
        }
        self.credentials.update(self.identifier)

    def check_response_for_errors(self, resp):
        if not resp.ok and ("Password is required" in resp.text or "Password is too weak" in resp.text):
            return resp
        return super().check_response_for_errors(resp)
