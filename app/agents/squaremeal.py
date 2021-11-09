from soteria.configuration import Configuration
import settings
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    GENERAL_ERROR,
    AgentError,
    LoginError,
)

class SquaremealBase(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.base_url = config.merchant_url
        # self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["token"]
        # self.secondary_key = config.security_credentials["outbound"]["credentials"][1]["value"]["token"]
        # self.headers = {"bpl-user-channel": self.channel, "Authorization": f"Token {self.auth}", "Secondary-Key": {self.secondary_key}}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)


class Squaremeal(SquaremealBase):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)


    def join(self, credentials):
        consents = credentials.get("consents", [])
        url = f"{self.base_url}register"
        payload = {
            "email": "",
            "password": "",
            "FirstName": "",
            "LastName": "",
            "Source": "Bink"
        }
        try:
            resp = self.make_request(url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)

        # newsletter_optin = self._get_newsletter_consent(self, consents)
        newsletter_optin = False

        if newsletter_optin:
            url = f"{self.base_url}update/newsletter"
            payload = {
                "Newsletter": "Weekly restaurants and bars news",
                "Subscription": "true"
            }
            try:
                self.make_request(url, method="post", json=payload)
            except (LoginError, AgentError) as ex:
                self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)
