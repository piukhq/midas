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


class Bpl(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        self.callback_url = config.callback_url
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth}"}
        self.errors = {
            GENERAL_ERROR: ["MALFORMED_REQUEST", "INVALID_TOKEN", "INVALID_RETAILER", "FORBIDDEN"],
            ACCOUNT_ALREADY_EXISTS: ["ACCOUNT_EXISTS"],
            STATUS_REGISTRATION_FAILED: ["MISSING_FIELDS", "VALIDATION_FAILED"],
            STATUS_LOGIN_FAILED: ["NO_ACCOUNT_FOUND"],
        }
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.ASYNC_INTEGRATION][1].upper()

    def join(self, credentials):
        consents = credentials.get("consents", [])
        marketing_optin = consents[0]["value"] if consents else False
        url = f"{self.base_url}enrolment"
        payload = {
            "credentials": credentials,
            "marketing_preferences": [{"key": "marketing_pref", "value": marketing_optin}],
            "callback_url": self.callback_url,
            "third_party_identifier": hash_ids.encode(self.user_info["scheme_account_id"]),
        }

        try:
            self.make_request(url, method="post", audit=True, json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["code"], unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True
            if consents:
                self.consent_confirmation(consents, ConsentStatus.SUCCESS)

    def login(self, credentials):
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        # If merchant_identifier already exists do not get by credentials
        if "merchant_identifier" in credentials.keys():
            return
        # Channel not available for ADD journey.
        self.headers = {"bpl-user-channel": "com.bink.wallet", "Authorization": f"Token {self.auth}"}
        url = f"{self.base_url}getbycredentials"
        payload = {
            "email": credentials["email"],
            "account_number": credentials["card_number"],
        }

        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["code"], unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True

        membership_data = resp.json()
        credentials["merchant_identifier"] = membership_data["UUID"]
        self.identifier = {"merchant_identifier": membership_data["UUID"]}
        self.user_info["credentials"].update(self.identifier)

    @staticmethod
    def _make_pending_vouchers(vouchers):
        return [
            Voucher(
                issue_date=voucher["created_date"],
                redeem_date=voucher.get("redeemed_date"),
                expiry_date=voucher["conversion_date"],
                code=generate_pending_voucher_code(voucher["conversion_date"]),
                target_value=None,
                value=None,
                type=VoucherType.ACCUMULATOR.value,
                state="issued",
            )
            for voucher in vouchers
        ]

    @staticmethod
    def _make_issued_vouchers(vouchers):
        return [
            Voucher(
                issue_date=voucher["issued_date"],
                redeem_date=voucher.get("redeemed_date"),
                expiry_date=voucher["expiry_date"],
                code=voucher["code"],
                target_value=None,
                value=None,
                type=VoucherType.ACCUMULATOR.value,
                state=voucher["status"],
            )
            for voucher in vouchers
        ]

    def balance(self) -> Optional[Balance]:
        credentials = self.user_info["credentials"]
        merchant_id = credentials["merchant_identifier"]
        self.headers = {"bpl-user-channel": "com.bink.wallet", "Authorization": f"Token {self.auth}"}
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
                    type=VoucherType.ACCUMULATOR.value,
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
        self.user_info["credentials"].update(self.identifier)

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
