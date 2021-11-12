import settings

from soteria.configuration import Configuration

from app.agents.base import ApiMiner
from app.agents.exceptions import (
    GENERAL_ERROR,
    AgentError,
    LoginError,
)
from app.agents.schemas import Balance, Transaction


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
        self.channel = user_info.get("channel", "Bink")
        self.point_transactions = []
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.headers = {"Authorization":"", "Secondary-Key": self.secondary_key}


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
            "Source": self.channel
        }
        try:
            resp = self.make_request(url, method="post", json=payload)
            resp_json = resp.json()
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

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
                self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

    def login(self, credentials):
        if credentials.get("merchant_identifier"):
            return

        url = f"{self.base_url}login"
        payload = {
            "email": credentials["email"],
            "password": credentials["password"]
        }
        try:
            resp = self.make_request(url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

        membership_data = resp.json()
        self.identifier = {
            "merchant_identifier": membership_data["UserId"],
            "card_number": membership_data["MembershipNumber"]
        }
        self.user_info["credentials"].update(self.identifier)

    def scrape_transactions(self):
        return self.point_transactions

    def parse_transaction(self, transaction: dict):
        return Transaction(
            date=transaction["ConfirmedDate"],
            points=transaction["AwardedPoints"],
            description=transaction["EarnReason"]
        )

    def balance(self):
        credentials = self.user_info["credentials"]
        merchant_id = credentials["merchant_identifier"]
        url = f"{self.base_url}points/{merchant_id}"
        resp = self.make_request(url, method="get")

        points_data = resp.json()
        self.point_transactions = points_data["PointsActivity"]

        total_points = points_data["TotalPoints"]
        tier = points_data["LoyaltyTier"]
        return Balance(
            points=total_points,
            value=0,
            value_label="",
            reward_tier=tier,
        )

