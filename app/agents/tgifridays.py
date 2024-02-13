import decimal
import hashlib
import hmac
import json
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

from requests.models import Response
from blinker import signal
from requests import HTTPError
from soteria.configuration import Configuration

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.encryption import get_secret
from app.exceptions import AccountAlreadyExistsError, NoSuchRecordError, UnknownError
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

    def check_response_for_errors(self, resp) -> Response | HTTPError:
        try:
            resp.raise_for_status()
        except HTTPError:
            raise
        return resp

    def _get_vault_secrets(self, secret_names: list) -> list:
        secrets = []
        try:
            for secret in secret_names:
                secrets.append(get_secret(secret))
        except Exception:
            raise

        return secrets

    @staticmethod
    def _generate_signature(uri, body, secret) -> str:
        path = "/" + uri
        request_body = json.dumps(body)
        payload = "".join((path, (request_body)))
        return hmac.new(bytes(secret, "UTF-8"), bytes(payload, "UTF-8"), hashlib.sha256).hexdigest()

    def _get_user_information(self) -> dict:
        admin_key = self._get_vault_secrets(["tgi-fridays-admin-key"])[0]
        self.headers.update(
            {
                "Authorization": f"Bearer {admin_key}",
            }
        )
        resp = self.make_request(
            urljoin(self.base_url, "api2/dashboard/users/info"),
            method="get",
            json={"user_id": self.credentials["merchant_identifier"]},
        )
        return resp.json()

    def _generate_punchh_app_device_id(self):
        id = self.user_info["bink_user_id"] + str(self.user_info["scheme_account_id"])
        return hashlib.sha256(id.encode("utf-8")).hexdigest()

    def join(self) -> None:
        client_id, secret = self._get_vault_secrets(["tgi-fridays-client-id", "tgi-fridays-secret"])
        uri = "api2/mobile/users"
        payload = {
            "client": client_id,
            "user": {
                "first_name": self.credentials["first_name"],
                "last_name": self.credentials["last_name"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "password_confirmation": self.credentials["password"],
                "marketing_email_subscription": self.credentials["consents"][0]["value"],
            },
        }
        self.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "bink",
                "punchh-app-device-id": self._generate_punchh_app_device_id(),
                "x-pch-digest": self._generate_signature(uri, payload, secret),
            }
        )
        try:
            resp = self.make_request(urljoin(self.base_url, uri), method="post", audit=True, data=json.dumps(payload))
        except Exception as e:
            if (
                e.response.status_code == 422  # type:ignore
                and "device_already_shared" in e.response.text  # type:ignore
                or "Email has already been taken" in e.response.text  # type:ignore
            ):
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=AccountAlreadyExistsError,
                )
                raise AccountAlreadyExistsError(exception=e)
            else:
                super().check_response_for_errors(resp)

        resp_json = resp.json()
        user_id = resp_json["user"]["user_id"]
        self.identifier = {"merchant_identifier": user_id}
        self.credentials.update(self.identifier)

    def login(self) -> None:
        try:
            user_information = self._get_user_information()
        except HTTPError as e:
            if e.response.status_code == 404:
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=NoSuchRecordError,
                )
                raise NoSuchRecordError(exception=e)
            else:
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=UnknownError,
                )
                raise UnknownError(exception=e)
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
