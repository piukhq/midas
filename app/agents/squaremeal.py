import settings
import requests

import arrow
import json
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

from app.scheme_account import JourneyTypes
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    GENERAL_ERROR,
    AgentError,
    LoginError,
)
from app.agents.schemas import Balance, Transaction
from app.reporting import get_logger

log = get_logger("squaremeal-restaurant-rewards")


class Squaremeal(ApiMiner):
    token_store = UserTokenStore(settings.REDIS_URL)
    AUTH_TOKEN_TIMEOUT = 3599

    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.base_url = config.merchant_url
        self.auth_url = config.security_credentials["outbound"]["credentials"][0]["value"]["url"]
        self.secondary_key = str(config.security_credentials["outbound"]["credentials"][0]["value"]["secondary-key"])
        self.channel = user_info.get("channel", "Bink")
        self.journey_type = user_info["journey_type"]
        self.point_transactions = []
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    def authenticate(self):
        have_valid_token = False
        current_timestamp = (arrow.utcnow().int_timestamp,)
        token = {}
        try:
            token = json.loads(self.token_store.get(self.scheme_id))
            try:
                if self._token_is_valid(token, current_timestamp):
                    have_valid_token = True
            except (KeyError, TypeError) as ex:
                log.exception(ex)
        except (KeyError, self.token_store.NoSuchToken):
            pass

        if not have_valid_token:
            sm_access_token = self._refresh_token()
            token = self._store_token(sm_access_token, current_timestamp)

        return token["sm_access_token"]

    def _refresh_token(self):
        url = self.auth_url
        payload = {
            "grant_type": "client_credentials",
            "client_secret": settings.AZURE_SM_CLIENT_SECRET,
            "client_id": settings.AZURE_SM_CLIENT_ID,
            "scope": settings.AZURE_SM_SCOPE,
        }
        resp = requests.post(url, data=payload)
        token = resp.json()["access_token"]
        return token

    def _store_token(self, token, current_timestamp):
        token = {
            "sm_access_token": token,
            "timestamp": current_timestamp,
        }
        self.token_store.set(scheme_account_id=self.scheme_id, token=json.dumps(token))
        return token

    def _token_is_valid(self, token, current_timestamp):
        time_diff = current_timestamp[0] - token["timestamp"][0]
        return time_diff < self.AUTH_TOKEN_TIMEOUT

    def join(self, credentials):
        consents = credentials.get("consents", [])
        url = f"{self.base_url}register"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
        payload = {
            "email": credentials["email"],
            "password": credentials["password"],
            "FirstName": credentials["first_name"],
            "LastName": credentials["last_name"],
            "Source": self.channel,
        }
        try:
            resp = self.make_request(url, method="post", json=payload)
            resp_json = resp.json()
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

        membership_data = resp_json
        self.identifier = {
            "merchant_identifier": membership_data["UserId"],
            "card_number": membership_data["MembershipNumber"],
        }
        self.user_info["credentials"].update(self.identifier)

        user_id = resp_json["UserId"]
        newsletter_optin = consents[0]["value"] if consents else False
        if newsletter_optin:
            url = f"{self.base_url}update/newsletters/{user_id}"
            payload = [{"Newsletter": "Weekly restaurants and bars news", "Subscription": "true"}]
            try:
                self.make_request(url, method="put", json=payload)
            except Exception as ex:
                self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

    def login(self, credentials):
        # SM is not supposed to login as part of the JOIN journey
        if self.journey_type == JourneyTypes.JOIN:
            return

        url = f"{self.base_url}login"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
        payload = {"email": credentials["email"], "password": credentials["password"]}
        try:
            self.make_request(url, method="post", json=payload)
        except (LoginError, AgentError) as ex:
            self.handle_errors(ex.response.json(), unhandled_exception_code=GENERAL_ERROR)

    def scrape_transactions(self):
        return self.point_transactions

    def parse_transaction(self, transaction: dict):
        return Transaction(
            date=transaction["ConfirmedDate"],
            points=transaction["AwardedPoints"],
            description=transaction["EarnReason"],
        )

    def balance(self):
        credentials = self.user_info["credentials"]
        merchant_id = credentials["merchant_identifier"]
        url = f"{self.base_url}points/{merchant_id}"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
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
