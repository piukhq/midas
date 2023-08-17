import base64
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from blinker import signal
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Voucher
from app.exceptions import AccountAlreadyExistsError, BaseError, ConfigurationError, WeakPassword
from app.reporting import get_logger
from app.vouchers import VoucherState, voucher_state_names

RETRY_LIMIT = 3
log = get_logger("slim-chickens")


class SlimChickens(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.integration_service = "SYNC"
        self.credentials = self.user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.outbound_security = self.config.security_credentials["outbound"]["credentials"][0]["value"]

    def _authenticate(self, username: str, password: str):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        else:
            try:
                auth_credentials = f"{username}:{password}"
                auth_header_value = base64.b64encode(auth_credentials.encode()).decode()
                self.headers["Authorization"] = f"Basic {auth_header_value}"
            except (KeyError, TypeError) as e:
                raise ConfigurationError(exception=e) from e

    def _account_already_exists(self) -> bool:
        self._authenticate(username=self.outbound_security["username"], password=self.outbound_security["password"])
        payload = {
            "username": self.credentials["email"],
            "channels": [{"channelKey": self.outbound_security["channel_key"]}],
        }
        resp = self.make_request(self.url, method="post", audit=True, json=payload)
        resp_json = resp.json()
        if "Password is required" in resp_json.get("errors", {}).values():
            return False
        else:
            return True

    def login(self) -> None:
        self._authenticate(username=self.credentials["email"], password=self.credentials["password"])

    def balance(self) -> Balance | None:
        resp = self.make_request(
            urljoin(self.base_url, "/search"),
            json={"channelKeys": [self.outbound_security["channel_key"]], "types": ["wallet"]},
        )
        vouchers = resp.json()["wallet"]
        in_progress = None
        issued = []

        for voucher in vouchers:
            if "cardPoints" in voucher:
                in_progress = Voucher(
                    state=voucher_state_names[VoucherState.IN_PROGRESS],
                    code=voucher["voucherCode"],
                    issue_date=voucher["start"],
                    expiry_date=voucher["voucherExpiry"],
                )
            else:
                issued.append(
                    Voucher(
                        state=voucher_state_names[VoucherState.ISSUED],
                        code="----------",
                        issue_date=voucher["start"],
                        expiry_date=voucher["voucherExpiry"],
                    )
                )
        if in_progress is None:
            raise BaseError

        return Balance(points=Decimal(0), value=Decimal(0), value_label="", vouchers=[in_progress, *issued])

    def join(self) -> Any:
        self.url = urljoin(self.base_url, f"core/account/{self.outbound_security['account_key']}/consumer")
        marketing_mapping = {i["slug"]: i["value"] for i in self.credentials["consents"]}
        try:
            account_exists = self._account_already_exists()
        except BaseError:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise
        if not account_exists:
            payload = {
                "firstName": self.credentials["first_name"],
                "lastName": self.credentials["last_name"],
                "username": self.credentials["email"],
                "password": self.credentials["password"],
                "dob": self.credentials["date_of_birth"],
                "attributes": {"optin2": marketing_mapping.get("optin2")},
                "channels": [{"channelKey": self.outbound_security["channel_key"]}],
            }
            try:
                resp = self.make_request(self.url, method="post", audit=True, json=payload)
                resp_json = resp.json()
                if "Password is too weak" in resp_json.get("errors", {}).values():
                    raise WeakPassword()
                signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
            except BaseError:
                signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
                raise
        else:
            raise AccountAlreadyExistsError()  # The join journey ends

        response_data = resp.json()
        self.identifier = {
            "merchant_identifier": response_data["consumer"]["email"],
        }
        self.credentials.update(self.identifier)

    def check_response_for_errors(self, resp):
        if not resp.ok and ("Password is required" in resp.text or "Password is too weak" in resp.text):
            return resp
        return super().check_response_for_errors(resp)
