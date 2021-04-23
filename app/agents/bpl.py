from app.agents.base import ApiMiner
from app.configuration import Configuration


class Trenette(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        self.callback_url = config.callback_url
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth}"}

    def register(self, credentials):
        payload = {
            "credentials": credentials,
            "marketing_preferences": [],
            "callback_url": self.callback_url,
        }

        self.make_request(self.base_url, method="post", json=payload)

    def login(self, credentials):
        pass
