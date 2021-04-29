from app.agents.base import ApiMiner
from app.configuration import Configuration
from app.agents.exceptions import (
    AgentError, LoginError, RegistrationError,
    GENERAL_ERROR,
    ACCOUNT_ALREADY_EXISTS,
    UNKNOWN,
    STATUS_LOGIN_FAILED,
    NO_SUCH_RECORD,
)


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
            ACCOUNT_ALREADY_EXISTS: ["ACCOUNT_EXISTS"]
        }

    def register(self, credentials):
        payload = {
            "credentials": credentials,
            "marketing_preferences": [],
            "callback_url": self.callback_url,
        }

        # resp = self.make_request(self.base_url, method="post", json=payload)
        # error_msg = resp.json()["error"]
        # if error_msg:
        #     self.handle_errors(error_msg, exception_type=(LoginError, AgentError))
        #
        # self.expecting_callback = True

        try:
            resp = self.make_request(self.base_url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"])
        else:
            self.expecting_callback = True

    def login(self, credentials):
        pass