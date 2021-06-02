from uuid import uuid4
from decimal import Decimal
from urllib.parse import urljoin

import settings
from app import publish

from app.vouchers import VoucherState, VoucherType, voucher_state_names
from app.agents.base import ApiMiner
from app.configuration import Configuration
from app.agents.exceptions import (
    AgentError, LoginError,
    GENERAL_ERROR,
    ACCOUNT_ALREADY_EXISTS,
    STATUS_REGISTRATION_FAILED
)
from app.encryption import hash_ids
from app.utils import SchemeAccountStatus


class BplBase(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        self.callback_url = config.callback_url
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth}"}
        self.errors = {
            GENERAL_ERROR: ["MALFORMED_REQUEST", "INVALID_TOKEN", "INVALID_RETAILER", "FORBIDDEN"],
            ACCOUNT_ALREADY_EXISTS: ["ACCOUNT_EXISTS"],
            STATUS_REGISTRATION_FAILED: ["MISSING_FIELDS", "VALIDATION_FAILED"]
        }

    def update_async_join(self, data):
        decoded_scheme_account = hash_ids.decode(data["third_party_identifier"])
        scheme_account_id = decoded_scheme_account[0]
        self.update_hermes_credentials(data, scheme_account_id)
        status = SchemeAccountStatus.ACTIVE
        publish.status(scheme_account_id, status, uuid4(), self.user_info, journey='join')

    def update_hermes_credentials(self, customer_details, scheme_account_id):

        self.identifier = {
            "card_number": customer_details["account_number"], "merchant_identifier": customer_details["UUID"]
        }
        self.user_info["credentials"].update(self.identifier)

        # for updating user ID credential you get for registering (e.g. getting issued a card number)
        api_url = urljoin(
            settings.HERMES_URL, f"schemes/accounts/{scheme_account_id}/credentials",
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


class Trenette(BplBase):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    def register(self, credentials):

        url = f"{self.base_url}enrolment"
        payload = {
            "credentials": credentials,
            "marketing_preferences": [],
            "callback_url": self.callback_url,
            "third_party_identifier": hash_ids.encode(self.user_info['scheme_account_id']),
        }

        try:
            self.make_request(url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True

    def login(self, credentials):
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

        resp = self.make_request(url, method="post", json=payload)

        membership_data = resp.json()
        credentials["merchant_identifier"] = membership_data["UUID"]
        self.identifier = {"merchant_identifier": membership_data["UUID"]}
        self.user_info["credentials"].update(self.identifier)

    def balance(self):
        credentials = self.user_info["credentials"]
        merchant_id = credentials["merchant_identifier"]
        self.headers = {"bpl-user-channel": "com.bink.wallet", "Authorization": f"Token {self.auth}"}
        url = f"{self.base_url}{merchant_id}"
        resp = self.make_request(url, method="get")
        bpl_data = resp.json()
        scheme_account_id = self.user_info["scheme_account_id"]
        self.update_hermes_credentials(bpl_data, scheme_account_id)
        if len(bpl_data["current_balances"]) == 0:
            return None

        balance = bpl_data["current_balances"][0]["value"]

        return {
            "points": Decimal(balance),
            "value": Decimal(balance),
            "value_label": "",
            "vouchers": [
                {"state": voucher_state_names[VoucherState.IN_PROGRESS],
                 "type": VoucherType.STAMPS.value,
                 "target_value": None,
                 "value": Decimal(balance)},
            ],
        }
