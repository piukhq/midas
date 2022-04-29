from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin
from uuid import uuid4

from soteria.configuration import Configuration

import settings
from app import publish
from app.agents.base import BaseAgent
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    GENERAL_ERROR,
    STATUS_LOGIN_FAILED,
    STATUS_REGISTRATION_FAILED,
    AgentError,
    LoginError,
)
from app.agents.schemas import Balance, Transaction, Voucher
from app.encryption import hash_ids
from app.reporting import get_logger
from app.scheme_account import SchemeAccountStatus
from app.tasks.resend_consents import ConsentStatus
from app.vouchers import VoucherState, VoucherType, generate_pending_voucher_code, voucher_state_names

log = get_logger("bpl-agent")


def voucher_type(scheme_slug: str) -> int:
    """
    This function can be removed once hermes has been fixed to use the voucher types set in it's django database.
    Loyalty jira: https://hellobink.atlassian.net/browse/LOY-2405
    We should be able to remove the type field where this function is called.
    3 calls to this function will also need to be removed when the time comes.
    """
    stamp_schemes = [
        "bpl-cortado",
    ]
    if scheme_slug in stamp_schemes:
        return VoucherType.STAMPS.value

    return VoucherType.ACCUMULATOR.value


class Bpl(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(
            retry_count, user_info, config_handler_type=Configuration.JOIN_HANDLER, scheme_slug=scheme_slug
        )
        self.source_id = "bpl"
        self.credentials = user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.callback_url = self.config.callback_url
        self.auth_token = self.config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth_token}"}
        self.integration_service = "ASYNC"
        self.errors = {
            GENERAL_ERROR: ["MALFORMED_REQUEST", "INVALID_TOKEN", "INVALID_RETAILER", "FORBIDDEN"],
            ACCOUNT_ALREADY_EXISTS: ["ACCOUNT_EXISTS"],
            STATUS_REGISTRATION_FAILED: ["MISSING_FIELDS", "VALIDATION_FAILED"],
            STATUS_LOGIN_FAILED: ["NO_ACCOUNT_FOUND"],
        }

    def join(self):
        consents = self.credentials.get("consents", [])
        marketing_optin = consents[0]["value"] if consents else False
        url = f"{self.base_url}enrolment"
        payload = {
            "credentials": self.credentials,
            "marketing_preferences": [{"key": "marketing_pref", "value": marketing_optin}],
            "callback_url": self.callback_url,
            "third_party_identifier": hash_ids.encode(self.user_info["scheme_account_id"]),
        }

        try:
            self.make_request(url, method="post", audit=True, json=payload)
        except (LoginError, AgentError) as ex:
            error_code = ex.response.json()["code"] if ex.response is not None else ex.args[0]
            self.handle_errors(error_code, unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True
            if consents:
                self.consent_confirmation(consents, ConsentStatus.SUCCESS)

    def login(self):
        self.integration_service = "SYNC"
        # If merchant_identifier already exists do not get by credentials
        if "merchant_identifier" in self.credentials.keys():
            return
        # Channel not available for ADD journey.
        self.headers["bpl-user-channel"] = "com.bink.wallet"
        url = f"{self.base_url}getbycredentials"
        payload = {
            "email": self.credentials["email"],
            "account_number": self.credentials["card_number"],
        }

        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
        except (LoginError, AgentError) as ex:
            error_code = ex.response.json()["code"] if ex.response is not None else ex.args[0]
            self.handle_errors(error_code, unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True

        membership_data = resp.json()
        self.credentials["merchant_identifier"] = membership_data["UUID"]
        self.identifier = {"merchant_identifier": membership_data["UUID"]}
        self.credentials.update(self.identifier)

    def _make_pending_vouchers(self, vouchers):
        return [
            Voucher(
                issue_date=voucher["created_date"],
                redeem_date=voucher.get("redeemed_date"),
                expiry_date=voucher["conversion_date"],
                code=generate_pending_voucher_code(voucher["conversion_date"]),
                target_value=None,
                value=None,
                type=voucher_type(self.scheme_slug),
                state="issued",
            )
            for voucher in vouchers
        ]

    def _make_issued_vouchers(self, vouchers):
        return [
            Voucher(
                issue_date=voucher["issued_date"],
                redeem_date=voucher.get("redeemed_date"),
                expiry_date=voucher["expiry_date"],
                code=voucher["code"],
                target_value=None,
                value=None,
                type=voucher_type(self.scheme_slug),
                state=voucher["status"],
            )
            for voucher in vouchers
        ]

    def balance(self) -> Optional[Balance]:
        merchant_id = self.credentials["merchant_identifier"]
        self.headers["bpl-user-channel"] = "com.bink.wallet"
        url = f"{self.base_url}{merchant_id}"
        resp = self.make_request(url, method="get")
        bpl_data = resp.json()
        scheme_account_id = self.user_info["scheme_account_id"]
        self.update_hermes_credentials(bpl_data, scheme_account_id)
        vouchers = bpl_data["rewards"]
        pending_vouchers = bpl_data["pending_rewards"]
        if len(bpl_data["current_balances"]) == 0:
            return None

        balance = Decimal(str(bpl_data["current_balances"][0]["value"]))

        return Balance(
            points=balance,
            value=balance,
            value_label="",
            vouchers=[
                Voucher(
                    state=voucher_state_names[VoucherState.IN_PROGRESS],
                    type=voucher_type(self.scheme_slug),
                    target_value=None,
                    value=balance,
                ),
                *self._make_issued_vouchers(vouchers),
                *self._make_pending_vouchers(pending_vouchers),
            ],
        )

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            log.warning(f"{self} failed to get transactions: {repr(ex)}")
            return []

    def transaction_history(self) -> list[Transaction]:
        raise NotImplementedError()

    def update_async_join(self, data):
        decoded_scheme_account = hash_ids.decode(data["third_party_identifier"])
        scheme_account_id = decoded_scheme_account[0]
        self.update_hermes_credentials(data, scheme_account_id)
        status = SchemeAccountStatus.ACTIVE
        publish.status(scheme_account_id, status, uuid4(), self.user_info, journey="join")

    def update_hermes_credentials(self, customer_details, scheme_account_id):

        self.identifier = {
            "card_number": customer_details["account_number"],
            "merchant_identifier": customer_details["UUID"],
        }
        self.credentials.update(self.identifier)

        # for updating user ID credential you get for joining (e.g. getting issued a card number)
        api_url = urljoin(
            settings.HERMES_URL,
            f"schemes/accounts/{scheme_account_id}/credentials",
        )
        headers = {
            "Content-type": "application/json",
            "Authorization": "token " + settings.SERVICE_API_KEY,
        }
        super().make_request(  # Don't want to call any signals for internal calls
            api_url,
            method="put",
            timeout=10,
            json=self.identifier,
            headers=headers,
        )
