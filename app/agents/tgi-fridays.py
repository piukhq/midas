from decimal import Decimal
import decimal
from typing import Optional
from urllib.parse import urljoin

from blinker import signal
from requests import HTTPError
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import (
    AccountAlreadyExistsError,
)
from app.reporting import get_logger

RETRY_LIMIT = 3

log = get_logger("tgi-fridays")


class TGIFridays(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.base_url = self.config.merchant_url
        self.credentials = self.user_info["credentials"]
        self._points_balance = Decimal("0")
        decimal.getcontext().rounding = decimal.ROUND_HALF_UP  # ensures that 0.5's are rounded up

    def _get_user_information(self) -> dict:
        resp = self.make_request(
            urljoin(self.base_url, "api2/dashboard/users/info"),
            method="get",
            json={"user_id": self.credentials["merchant_identifier"]},
        )
        return resp.json()

    def check_response_for_errors(self, resp):
        try:
            resp.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 422 and "device_already_shared" in e.response.text:
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=AccountAlreadyExistsError,
                )
                raise AccountAlreadyExistsError(exception=e)

        resp = super().check_response_for_errors(resp)

        return resp

    def join(self) -> None:
        self.url = urljoin(self.base_url, "api2/mobile/users")
        payload = {
            "user": {
                "first_name": self.credentials["first_name"],
                "last_name": self.credentials["last_name"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "password_confirmation": self.credentials["password"],
                "marketing_email_subscription": self.credentials["consents"][0]["value"],
            },
        }
        resp = self.make_request(self.url, method="post", audit=True, json=payload)

        resp_json = resp.json()
        user_id = resp_json["user"]["user_id"]
        self.identifier = {"merchant_identifier": user_id}
        self.credentials.update({"merchant_identifier": user_id})

    def login(self) -> None:
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
