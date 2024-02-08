import decimal
import hashlib
import hmac
import json
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin
from uuid import uuid4

import responses
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from blinker import signal
from requests import HTTPError
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential

import settings
from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.exceptions import AccountAlreadyExistsError, NoSuchRecordError, UnknownError
from app.reporting import get_logger

RETRY_LIMIT = 3

log = get_logger("tgi-fridays")


class TGIFridays(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(
            retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug
        )
        self.base_url = self.config.merchant_url
        self.credentials = self.user_info["credentials"]
        self._points_balance = Decimal("0")
        decimal.getcontext().rounding = (
            decimal.ROUND_HALF_UP
        )  # ensures that 0.5's are rounded up

    def _get_user_information(self) -> dict:
        resp = self.make_request(
            urljoin(self.base_url, "api2/dashboard/users/info"),
            method="get",
            json={"user_id": self.credentials["merchant_identifier"]},
        )
        return resp.json()

    def check_response_for_errors(self, resp) -> responses.Response:
        try:
            resp.raise_for_status()
        except HTTPError:
            raise
        return resp

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_vault_secrets(self) -> list:
        kv_credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_interactive_browser_credential=True,
            additionally_allowed_tenants=[settings.AZURE_AAD_TENANT_ID],
        )
        client = SecretClient(vault_url=settings.VAULT_URL, credential=kv_credential)
        key_items = []
        try:
            for item in [
                "tgi-fridays-client-id",
                "tgi-fridays-secret",
                "tgi-fridays-admin-key",
            ]:
                key_items.append(client.get_secret(item).value)
        except Exception:
            raise

        return key_items

    def _generate_signature(self, uri, body, secret) -> str:
        path = "/" + uri
        request_body = json.dumps(body)
        payload = "".join((path, (request_body)))
        return hmac.new(
            bytes(secret, "UTF-8"), bytes(payload, "UTF-8"), hashlib.sha256
        ).hexdigest()

    def join(self) -> None:
        self.credentials.update({"punchh_app_device_id": str(uuid4())})
        client_id, secret, admin_key = self._get_vault_secrets()

        uri = "api2/mobile/users"

        self.url = urljoin(self.base_url, uri)
        payload = {
            "client": client_id,
            "user": {
                "first_name": self.credentials["first_name"],
                "last_name": self.credentials["last_name"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "password_confirmation": self.credentials["password"],
                "marketing_email_subscription": self.credentials["consents"][0][
                    "value"
                ],
            },
        }
        self.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "bink",
                "punchh-app-device-id": self.credentials["punchh_app_device_id"],
                "x-pch-digest": self._generate_signature(uri, payload, secret),
                "Accept-Language": "",
                # "Authorization": f"Bearer {admin_key}",
            }
        )
        try:
            resp = self.make_request(
                self.url, method="post", audit=True, data=json.dumps(payload)
            )
        except Exception as e:
            if (
                e.response.status_code == 422
                and "device_already_shared" in e.response.text
                or "Email has already been taken" in e.response.text
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
        self.credentials.update({"merchant_identifier": user_id})

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
