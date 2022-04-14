from copy import deepcopy
from decimal import Decimal

from blinker import signal
from soteria.configuration import Configuration

import settings
from app.agents.base import BaseAgent
from app.agents.exceptions import AgentError, JoinError, LoginError
from app.agents.schemas import Balance, Transaction
from app.reporting import get_logger
from app.scheme_account import JourneyTypes
from app.tasks.resend_consents import ConsentStatus

RETRY_LIMIT = 3
log = get_logger("squaremeal")


class Squaremeal(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.source_id = "squaremeal"
        self.config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.base_url = self.config.merchant_url
        self.auth_url = self.config.security_credentials["outbound"]["credentials"][0]["value"]["url"]
        self.auth_token_timeout = 3599
        self.authentication_service = self.config.security_credentials["outbound"]["service"]
        self.headers["Secondary-Key"] = str(
            self.config.security_credentials["outbound"]["credentials"][0]["value"]["secondary-key"]
        )
        self.client_secret = self.config.security_credentials["outbound"]["credentials"][0]["value"]["client-secret"]
        self.client_id = self.config.security_credentials["outbound"]["credentials"][0]["value"]["client-id"]
        self.scope = self.config.security_credentials["outbound"]["credentials"][0]["value"]["scope"]

        self.channel = user_info.get("channel", "Bink")
        self.point_transactions = []
        self.errors = {
            "ACCOUNT_ALREADY_EXISTS": [422],
            "SERVICE_CONNECTION_ERROR": [401],
            "END_SITE_DOWN": [530],
        }
        self.integration_service = self.config.integration_service

    @staticmethod
    def hide_sensitive_fields(req_audit_logs):
        req_audit_logs_copy = deepcopy(req_audit_logs)
        try:
            for audit_log in req_audit_logs_copy:
                try:
                    audit_log.payload["password"] = "********"
                except TypeError:
                    continue

        except KeyError as e:
            log.warning(f"Unexpected payload format for Squaremeal audit log - Missing key: {e}")

        return req_audit_logs_copy

    def get_auth_url_and_payload(self):
        url = self.auth_url
        payload = {
            "grant_type": "client_credentials",
            "client_secret": self.client_secret,
            "client_id": self.client_id,
            "scope": self.scope,
        }
        return url, payload

    def _join(self, credentials):
        url = f"{self.base_url}register"
        self.authenticate()
        payload = {
            "email": credentials["email"],
            "password": credentials["password"],
            "FirstName": credentials["first_name"],
            "LastName": credentials["last_name"],
            "Source": self.channel,
        }
        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
            signal("join-success").send(self, slug=self.scheme_slug, channel=self.channel)
        except (AgentError, JoinError) as ex:
            signal("join-fail").send(self, slug=self.scheme_slug, channel=self.channel)
            error_code = ex.response.status_code if ex.response is not None else ex.code
            self.handle_errors(error_code)
        return resp.json()

    def _update_newsletters(self, user_id, consents):
        newsletter_optin = consents[0]["value"]
        user_choice = "true" if newsletter_optin else "false"
        url = "{}update/newsletters/{}".format(self.base_url, user_id)
        payload = [{"Newsletter": "Weekly restaurants and bars news", "Subscription": user_choice}]
        try:
            self.make_request(url, method="put", json=payload)
            self.consent_confirmation(consents, ConsentStatus.SUCCESS)
        except (AgentError, JoinError):
            pass

    def _login(self, credentials):
        url = f"{self.base_url}login"
        self.authenticate()
        payload = {"email": credentials["email"], "password": credentials["password"], "source": "com.barclays.bmb"}
        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
            signal("log-in-success").send(self, slug=self.scheme_slug)
        except (LoginError, AgentError) as ex:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            error_code = ex.response.status_code if ex.response is not None else ex.code
            self.handle_errors(error_code)
        return resp.json()

    def _get_balance(self):
        merchant_id = self.user_info["credentials"]["merchant_identifier"]
        url = f"{self.base_url}points/{merchant_id}"
        self.authenticate()
        try:
            resp = self.make_request(url, method="get")
        except (JoinError, AgentError) as ex:
            error_code = ex.response.status_code if ex.response is not None else ex.code
            self.handle_errors(error_code)
        return resp.json()

    def join(self, credentials):
        consents = credentials.get("consents", [])
        resp_json = self._join(credentials)
        self.identifier = {
            "merchant_identifier": resp_json["UserId"],
            "card_number": resp_json["MembershipNumber"],
        }
        self.user_info["credentials"].update(self.identifier)
        self._update_newsletters(resp_json["UserId"], consents)

    def login(self, credentials):
        # SM is not supposed to use login as part of the JOIN journey
        if self.journey_type == JourneyTypes.JOIN.value:
            return

        self.errors = {"STATUS_LOGIN_FAILED": [422], "SERVICE_CONNECTION_ERROR": [401], "END_SITE_DOWN": [530]}
        resp = self._login(credentials)
        self.identifier = {
            "merchant_identifier": resp["UserId"],
            "card_number": resp["MembershipNumber"],
        }
        self.user_info["credentials"].update(self.identifier)

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception as ex:
            log.warning(f"{self} failed to get transactions: {repr(ex)}")
            return []

    def transaction_history(self) -> list[Transaction]:
        transactions = [self.parse_transaction(tx) for tx in self.point_transactions]
        return transactions

    def parse_transaction(self, transaction: dict):
        return Transaction(
            date=transaction["ConfirmedDate"],
            points=Decimal(transaction["AwardedPoints"]),
            description=transaction["EarnReason"],
        )

    def balance(self):
        self.errors = {"NO_SUCH_RECORD": [422], "SERVICE_CONNECTION_ERROR": [401], "END_SITE_DOWN": [530]}
        points_data = self._get_balance()
        self.point_transactions = points_data["PointsActivity"]

        return Balance(
            points=Decimal(points_data["TotalPoints"]),
            value=Decimal("0"),
            value_label="",
            reward_tier=points_data["LoyaltyTier"],
        )
