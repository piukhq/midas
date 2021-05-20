from decimal import Decimal

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


class Trenette(ApiMiner):
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

    def register(self, credentials):
        payload = {
            "credentials": credentials,
            "marketing_preferences": [],
            "callback_url": self.callback_url,
            "third_party_identifier": hash_ids.encode(self.user_info['scheme_account_id']),
        }

        try:
            self.make_request(self.base_url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)
        else:
            self.expecting_callback = True

    def login(self, credentials):
        pass

    def balance(self):
        credentials = self.user_info["credentials"]
        merchant_id = credentials["merchant_identifier"]
        url = f"{self.base_url}{merchant_id}"
        resp = self.make_request(url, method="get")

        balance = resp.json()["current_balances"][0]["value"]
        return {
            "points": Decimal(balance),
            "value": Decimal(balance),
            "value_label": "",
            "vouchers": [
                {"state": voucher_state_names[VoucherState.IN_PROGRESS],
                 "type": VoucherType.STAMPS,
                 "value": balance,
                 "target_value": 0.0},

            ],
        }
