import base64
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import arrow
from blinker import signal
from requests.models import Response
from soteria.configuration import Configuration

from app import db
from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Voucher
from app.error_handler import handle_failed_login
from app.exceptions import AccountAlreadyExistsError, BaseError, CardNumberError, ConfigurationError, WeakPasswordError
from app.reporting import get_logger
from app.retry_util import delete_task, get_task
from app.vouchers import VoucherState, voucher_state_names

RETRY_LIMIT = 3
log = get_logger("slim-chickens")


def is_bink_voucher(voucher: dict) -> bool:
    if "cardPoints" in voucher:
        # in-progress vouchers don't have tags
        return True

    return any(tag["name"] == "Bink" for tag in voucher["offer"]["tags"])


class SlimChickens(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, Configuration.JOIN_HANDLER, scheme_slug=scheme_slug)
        self.integration_service = "SYNC"
        self.credentials = self.user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.outbound_security = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self.retry_task = None
        self.balance_vouchers = None

    def _configure_outbound_auth(self, username: str, password: str):
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
        self._configure_outbound_auth(
            username=self.outbound_security["username"], password=self.outbound_security["password"]
        )
        payload = {
            "username": self.credentials["email"],
            "channels": [{"channelKey": self.outbound_security["channel_key"]}],
        }
        resp = self.make_request(self.url, method="post", audit=False, json=payload)
        resp_json = resp.json()
        if "Password is required" in resp_json.get("errors", {}).values():
            return False
        else:
            return True

    def login(self) -> None:
        """
        There is no login, this will set the outbound auth headers
        with the account holder's credentials for the balance request
        """
        self._configure_outbound_auth(
            username=f"{self.credentials['email']}-{self.outbound_security['channel_key']}",
            password=self.credentials["password"],
        )
        # Balance request is made in the login so the correct errors can be raised for hermes
        resp = self.login_balance_request()

        if resp and self.user_info.get("from_join"):
            try:
                with db.session_scope() as session:
                    retry_task = get_task(session, self.user_info["scheme_account_id"])
                    delete_task(session, retry_task)
            except Exception:
                pass

        self.balance_vouchers = [] if not resp else resp.json().get("wallet", [])

    def transactions(self) -> list:
        return []

    def login_balance_request(self) -> Response | None:
        """
        If the search request fails during a join journey, it could mean that the account has not been created yet
        on Slim Chickens system. We therefore need to hold the balance request for a short time. The hold is using
        midas retry. Retry requires a function to call, some data and a retry time. If the following balance request
        fails, an exception is raised. If the current journey is a join and the error code is a 401, then we want
        to retry the balance request. Once the retry login/balance has succeeded, the retry task has to be deleted.
        Unfortunately we need to check the retry task for every balance request, then delete if one for the current
        scheme account id is found.
        """
        resp = None
        try:
            resp = self.make_request(
                urljoin(self.base_url, "search"),
                method="post",
                audit=True,
                json={
                    "channelKeys": [self.outbound_security["channel_key"]],
                    "types": ["wallet"],
                    "email": self.credentials["email"],
                },
            )
            signal("log-in-success").send(self, slug=self.scheme_slug)
        except BaseError as ex:
            error_code = ex.exception.response.status_code if ex.exception.response is not None else ex.code
            if self.user_info.get("from_join") and error_code == 401:
                log.warning(
                    f"{self.scheme_slug} account was not created in time, create retry task for login."
                    f"Scheme account id: {self.user_info['scheme_account_id']}"
                )
                with db.session_scope() as session:
                    handle_failed_login(self, session)
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            # Check the retry database for a login retry task (only for join journeys),
            # if there is one, do not raise error.
            # The next conditional is to handle the balance request made from Hermes
            if error_code == 401:
                try:
                    with db.session_scope() as session:
                        self.retry_task = get_task(session, self.user_info["scheme_account_id"])
                except Exception:
                    self.retry_task = None

                if not self.retry_task and self.user_info["journey_type"] > 0 and not self.user_info.get("from_join"):
                    raise CardNumberError()

        return resp

    @staticmethod
    def _voucher_date_to_timestamp(date: str) -> int:
        return arrow.get(date).int_timestamp

    def balance(self) -> Balance | None:
        vouchers = self.balance_vouchers
        in_progress = None
        issued = []

        points = Decimal("0")
        if self.retry_task and not vouchers:
            return Balance(points=points, value=Decimal(0), value_label="", vouchers=None)

        for voucher in vouchers:
            if not is_bink_voucher(voucher):
                continue

            if "cardPoints" in voucher:
                points = Decimal(voucher["cardPoints"])
                in_progress = Voucher(
                    state=voucher_state_names[VoucherState.IN_PROGRESS],
                    code=voucher["voucherCode"],
                    issue_date=self._voucher_date_to_timestamp(voucher["loyaltyScheme"]["stateChangedon"]),
                    expiry_date=self._voucher_date_to_timestamp(voucher["voucherExpiry"]),
                    value=points,
                )
            else:
                issued.append(
                    Voucher(
                        state=voucher_state_names[VoucherState.ISSUED],
                        code="----------",
                        issue_date=self._voucher_date_to_timestamp(voucher["offer"]["start"]),
                        expiry_date=self._voucher_date_to_timestamp(voucher["voucherExpiry"]),
                    )
                )

        if in_progress is None:
            raise BaseError

        return Balance(points=points, value=Decimal(0), value_label="", vouchers=[in_progress, *issued])

    def join(self) -> Any:
        self.url = urljoin(self.base_url, f"core/account/{self.outbound_security['account_key']}/consumer")
        marketing_mapping = {i["slug"]: i["value"] for i in self.credentials["consents"]}
        try:
            if not self._account_already_exists():
                payload = {
                    "firstName": self.credentials["first_name"],
                    "lastName": self.credentials["last_name"],
                    "username": self.credentials["email"],
                    "password": self.credentials["password"],
                    "email": self.credentials["email"],
                    "dob": self.credentials["date_of_birth"],
                    "attributes": {"optin2": marketing_mapping.get("optin2")},
                    "channels": [{"channelKey": self.outbound_security["channel_key"]}],
                }
                resp = self.make_request(self.url, method="post", audit=True, json=payload)
                resp_json = resp.json()
                if "Password is too weak" in resp_json.get("errors", {}).values():
                    raise WeakPasswordError()
                signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
            else:
                raise AccountAlreadyExistsError()
        except BaseError:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            raise  # The join journey ends

        response_data = resp.json()
        self.identifier = {
            "merchant_identifier": response_data["consumer"]["email"],
        }
        self.credentials.update(self.identifier)

    def check_response_for_errors(self, resp):
        if not resp.ok and ("Password is required" in resp.text or "Password is too weak" in resp.text):
            return resp
        return super().check_response_for_errors(resp)
