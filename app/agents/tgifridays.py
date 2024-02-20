import hashlib
import hmac
import json
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

from blinker import signal
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.encryption import hash_ids
from app.exceptions import AccountAlreadyExistsError, BaseError, NoSuchRecordError, StatusLoginFailedError, UnknownError
from app.reporting import get_logger
from app.scheme_account import JourneyTypes

RETRY_LIMIT = 3

log = get_logger("tgi-fridays")


class TGIFridays(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.base_url = self.config.merchant_url
        self.credentials = self.user_info["credentials"]
        self.secrets = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self._points_balance = Decimal("0")
        self.audit_config = {
            "audit_sensitive_keys": ["client", "password_confirmation"],
        }

    @staticmethod
    def _generate_signature(uri: str, body: dict, secret: str) -> str:
        path = "/" + uri
        request_body = json.dumps(body)
        payload = "".join((path, (request_body)))
        return hmac.new(bytes(secret, "UTF-8"), bytes(payload, "UTF-8"), hashlib.sha256).hexdigest()

    def _generate_punchh_app_device_id(self) -> str:
        return hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0])

    def _get_user_information(self) -> dict:
        self.errors = {
            NoSuchRecordError: [404],
        }
        self.headers.update({"Authorization": f'Bearer {self.secrets["admin_key"]}'})

        try:
            resp = self.make_request(
                urljoin(self.base_url, "api2/dashboard/users/info"),
                method="get",
                json={"user_id": self.credentials["merchant_identifier"]},
            )
        except BaseError as ex:
            error_code = ex.exception.response.status_code if ex.exception.response is not None else ex.code
            self.handle_error_codes(error_code)

        return resp.json()

    def _update_headers(self, uri, payload):
        self.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "bink",
                "punchh-app-device-id": self._generate_punchh_app_device_id(),
                "x-pch-digest": self._generate_signature(uri, payload, self.secrets["secret"]),
            }
        )

    def join(self) -> None:
        self.errors = {
            AccountAlreadyExistsError: [422],
        }
        uri = "api2/mobile/users"
        payload = {
            "client": self.secrets["client_id"],
            "user": {
                "first_name": self.credentials["first_name"],
                "last_name": self.credentials["last_name"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "password_confirmation": self.credentials["password"],
                "marketing_email_subscription": self.credentials["consents"][0]["value"],
            },
        }
        self._update_headers(uri, payload)
        try:
            resp = self.make_request(urljoin(self.base_url, uri), method="post", audit=True, json=payload)
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        except BaseError as ex:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            error_code = ex.exception.response.status_code if ex.exception.response is not None else ex.code
            self.handle_error_codes(error_code)

        self.identifier = {"merchant_identifier": resp.json()["user"]["user_id"]}
        self.credentials.update(self.identifier)

    def login(self) -> None:
        if self.user_info["journey_type"] == JourneyTypes.LINK:
            self.errors = {StatusLoginFailedError: [422], UnknownError: [400, 401, 412]}
            uri = "api2/mobile/users/login"
            payload = {
                "client": self.secrets["client_id"],
                "user": {
                    "email": self.credentials["email"],
                    "password": self.credentials["password"],
                },
            }
            self._update_headers(uri, payload)
            try:
                resp = self.make_request(
                    urljoin(self.base_url, uri), method="post", audit=True, data=json.dumps(payload)
                )
                signal("log-in-success").send(self, slug=self.scheme_slug)
            except BaseError as ex:
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                error_code = ex.exception.response.status_code if ex.exception.response is not None else ex.code
                self.handle_error_codes(error_code)
            self.identifier = {"merchant_identifier": resp.json()["user"]["user_id"]}
            self.credentials.update(self.identifier)

        user_information = self._get_user_information()
        self._points_balance = Decimal(user_information["balance"]["points_balance"])

    def balance(self) -> Optional[Balance]:
        return Balance(
            points=self._points_balance,
            value=self._points_balance,
            value_label="",
            vouchers=[],
        )

    def transactions(self) -> list[Transaction]:
        # No transactions to be listed for TGI-Fridays
        return []
