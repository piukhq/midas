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
        # endpoint = f"/bpl/loyalty/trenette/accounts/getbycredentials"
        # url = f"{self.base_url}{endpoint}"
        self.headers = {"bpl-user-channel": "com.bink.wallet", "Authorization": f"Token {self.auth}"}
        url = f"https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        payload = {
            "email": credentials["email"],
            "account_number": credentials["card_number"],
        }

        resp = self.make_request(url, method="post", json=payload)

        membership_data = resp.json()
        # self.credentials["merchant_identifier"] = membership_data["uuid"]
        # self.identifier = {"merchant_identifier": membership_data["uuid"]}
        # self.user_info["credentials"].update(self.identifier)

