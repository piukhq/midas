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
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]["url"]
        self.secondary_key = str(config.security_credentials["outbound"]["credentials"][0]["value"]["secondary-key"])
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"Authorization": "", "Secondary-Key": self.secondary_key}


class Squaremeal(SquaremealBase):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)


    def join(self, credentials):
        consents = credentials.get("consents", [])
        url = f"{self.base_url}register"
        payload = {
            "email": credentials["email"],
            "password": credentials["password"],
            "FirstName": credentials["first_name"],
            "LastName": credentials["last_name"],
            "Source": "Bink"
        }
        try:
            resp = self.make_request(url, method="post", json=payload)
            resp_json = resp.json()
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)

        user_id = resp_json["UserId"]
        newsletter_optin = consents[0]["value"] if consents else False
        if newsletter_optin:
            url = f"{self.base_url}update/newsletters/{user_id}"
            payload = [{
                "Newsletter": "Weekly restaurants and bars news",
                "Subscription": "true"
            }]
            try:
                self.make_request(url, method="put", json=payload)
            except Exception as ex:
                self.handle_errors(ex.response.json()["error"], unhandled_exception_code=GENERAL_ERROR)
