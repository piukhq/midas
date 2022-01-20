import json
from copy import deepcopy
from decimal import Decimal

import arrow
import requests
from blinker import signal
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential
from user_auth_token import UserTokenStore

import settings
from app.agents.base import ApiMiner, check_correct_authentication
from app.agents.exceptions import AgentError, JoinError, LoginError
from app.agents.schemas import Balance, Transaction
from app.reporting import get_logger
from app.scheme_account import JourneyTypes
from app.tasks.resend_consents import ConsentStatus

HANDLED_STATUS_CODES = [200, 201, 422, 401]
RETRY_LIMIT = 3
log = get_logger("squaremeal")


class Squaremeal(ApiMiner):
    token_store = UserTokenStore(settings.REDIS_URL)
    AUTH_TOKEN_TIMEOUT = 3599

    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.base_url = self.config.merchant_url
        self.auth_url = self.config.security_credentials["outbound"]["credentials"][0]["value"]["url"]
        self.headers["Secondary-Key"] = str(
            self.config.security_credentials["outbound"]["credentials"][0]["value"]["secondary-key"]
        )

        self.azure_sm_client_secret = self.config.security_credentials["outbound"]["credentials"][0]["value"][
            "client-secret"
        ]
        self.azure_sm_client_id = self.config.security_credentials["outbound"]["credentials"][0]["value"]["client-id"]
        self.azure_sm_scope = self.config.security_credentials["outbound"]["credentials"][0]["value"]["scope"]

        self.channel = user_info.get("channel", "Bink")
        self.point_transactions = []
        self.journey_type = self.user_info["journey_type"]
        self.errors = {
            "ACCOUNT_ALREADY_EXISTS": [422],
            "SERVICE_CONNECTION_ERROR": [401],
        }
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()

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

    def authenticate(self):
        have_valid_token = False
        current_timestamp = (arrow.utcnow().int_timestamp,)
        token_dict = {}
        try:
            token_dict = json.loads(self.token_store.get(self.scheme_id))
            try:
                if self._token_is_valid(token_dict, current_timestamp):
                    have_valid_token = True
            except (KeyError, TypeError) as ex:
                log.exception(ex)
        except (KeyError, self.token_store.NoSuchToken):
            pass

        if not have_valid_token:
            sm_access_token = self._refresh_token()
            token_dict = self._store_token(sm_access_token, current_timestamp)

        token = token_dict["sm_access_token"]
        self.headers["Authorization"] = f"Bearer {token}"

        return token

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _refresh_token(self):
        url = self.auth_url
        payload = {
            "grant_type": "client_credentials",
            "client_secret": self.azure_sm_client_secret,
            "client_id": self.azure_sm_client_id,
            "scope": self.azure_sm_scope,
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

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _create_account(self, credentials):
        url = f"{self.base_url}register"
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
            self.handle_errors(ex.response.status_code)
        return resp.json()

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
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

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _login(self, credentials):
        url = f"{self.base_url}login"
        payload = {"email": credentials["email"], "password": credentials["password"], "source": "com.barclays.bmb"}
        try:
            resp = self.make_request(url, method="post", audit=True, json=payload)
            signal("log-in-success").send(self, slug=self.scheme_slug)
        except (LoginError, AgentError) as ex:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            self.handle_errors(ex.response.status_code)
        return resp.json()

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_balance(self):
        merchant_id = self.user_info["credentials"]["merchant_identifier"]
        url = f"{self.base_url}points/{merchant_id}"
        try:
            resp = self.make_request(url, method="get")
        except (JoinError, AgentError) as ex:
            self.handle_errors(ex.response.status_code)
        return resp.json()

    def join(self, credentials):
        authentication_service = self.config.security_credentials["outbound"]["service"]
        check_correct_authentication(
            actual_config_auth_type=authentication_service,
            allowed_config_auth_types=[Configuration.OPEN_AUTH_SECURITY, Configuration.OAUTH_SECURITY],
        )
        if authentication_service == Configuration.OAUTH_SECURITY:
            self.authenticate()
        consents = credentials.get("consents", [])
        resp_json = self._create_account(credentials)
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
        authentication_service = self.config.security_credentials["outbound"]["service"]
        check_correct_authentication(
            actual_config_auth_type=authentication_service,
            allowed_config_auth_types=[Configuration.OPEN_AUTH_SECURITY, Configuration.OAUTH_SECURITY],
        )
        if authentication_service == Configuration.OAUTH_SECURITY:
            self.authenticate()
        self.errors = {
            "STATUS_LOGIN_FAILED": [422],
            "SERVICE_CONNECTION_ERROR": [401],
        }
        resp = self._login(credentials)
        self.identifier = {
            "merchant_identifier": resp["UserId"],
            "card_number": resp["MembershipNumber"],
        }
        self.user_info["credentials"].update(self.identifier)

    def scrape_transactions(self):
        return self.point_transactions

    def parse_transaction(self, transaction: dict):
        return Transaction(
            date=transaction["ConfirmedDate"],
            points=Decimal(transaction["AwardedPoints"]),
            description=transaction["EarnReason"],
        )

    def balance(self):
        authentication_service = self.config.security_credentials["outbound"]["service"]
        check_correct_authentication(
            actual_config_auth_type=authentication_service,
            allowed_config_auth_types=[Configuration.OPEN_AUTH_SECURITY, Configuration.OAUTH_SECURITY],
        )
        if authentication_service == Configuration.OAUTH_SECURITY:
            self.authenticate()
        self.errors = {
            "NO_SUCH_RECORD": [422],
            "SERVICE_CONNECTION_ERROR": [401],
        }
        points_data = self._get_balance()
        self.point_transactions = points_data["PointsActivity"]

        return Balance(
            points=Decimal(points_data["TotalPoints"]),
            value=Decimal("0"),
            value_label="",
            reward_tier=points_data["LoyaltyTier"],
        )
