import json
from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import arrow
import requests
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential
from user_auth_token import UserTokenStore

import settings
from app.agents.base import ApiMiner
from app.agents.exceptions import AgentError, JoinError
from app.agents.schemas import Balance, Transaction
from app.encryption import hash_ids
from app.reporting import get_logger
from app.tasks.resend_consents import ConsentStatus

HANDLED_STATUS_CODES = [200, 201, 422, 401]
RETRY_LIMIT = 3
log = get_logger("squaremeal")


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

        self.azure_sm_client_secret = config.security_credentials["outbound"]["credentials"][0]["value"][
            "client-secret"
        ]
        self.azure_sm_client_id = config.security_credentials["outbound"]["credentials"][0]["value"]["client-id"]
        self.azure_sm_scope = config.security_credentials["outbound"]["credentials"][0]["value"]["scope"]

        self.channel = user_info.get("channel", "Bink")
        self.point_transactions = []
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.journey_type = config.handler_type[1]
        self.errors = {
            "ACCOUNT_ALREADY_EXISTS": [422],
            "SERVICE_CONNECTION_ERROR": [401],
            "UNKNOWN": ["UNKNOWN"],
        }
        self.audit_logger.filter_fields = self.hide_sensitive_fields

    @staticmethod
    def hide_sensitive_fields(req_audit_logs):
        req_audit_logs_copy = deepcopy(req_audit_logs)
        try:
            for audit_log in req_audit_logs_copy:
                audit_log.payload["password"] = "********"

        except KeyError as e:
            log.warning(f"Unexpected payload format for Squaremeal audit log - Missing key: {e}")

        return req_audit_logs_copy

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

    def _log_audit_request(self, payload, message_uid, integration_service):
        record_uid = hash_ids.encode(self.scheme_id)
        self.audit_logger.add_request(
            payload=payload,
            scheme_slug=self.scheme_slug,
            message_uid=message_uid,
            record_uid=record_uid,
            handler_type=Configuration.JOIN_HANDLER,
            integration_service=integration_service,
        )

    def _log_audit_response(self, response, message_uid, integration_service):
        record_uid = hash_ids.encode(self.scheme_id)
        self.audit_logger.add_response(
            response=response,
            message_uid=message_uid,
            record_uid=record_uid,
            scheme_slug=self.scheme_slug,
            handler_type=Configuration.JOIN_HANDLER,
            status_code=response.status_code,
            integration_service=integration_service,
        )

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _create_account(self, credentials, message_uid, integration_service):
        url = f"{self.base_url}register"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
        payload = {
            "email": credentials["email"],
            "password": credentials["password"],
            "FirstName": credentials["first_name"],
            "LastName": credentials["last_name"],
            "Source": self.channel,
        }
        self._log_audit_request(payload, message_uid, integration_service)
        resp = self.make_request(url, method="post", json=payload)
        self._log_audit_response(resp, message_uid, integration_service)
        self.audit_logger.send_to_atlas()

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
        self.make_request(url, method="put", json=payload)
        self.consent_confirmation(consents, ConsentStatus.SUCCESS)

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _login(self, credentials):
        url = f"{self.base_url}login"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
        payload = {"email": credentials["email"], "password": credentials["password"]}
        self.make_request(url, method="post", json=payload)

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_balance(self):
        merchant_id = self.user_info["credentials"]["merchant_identifier"]
        url = f"{self.base_url}points/{merchant_id}"
        self.headers = {"Authorization": f"Bearer {self.authenticate()}", "Secondary-Key": self.secondary_key}
        resp = self.make_request(url, method="get")
        return resp.json()

    def join(self, credentials):
        consents = credentials.get("consents", [])
        message_uid = str(uuid4())
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        try:
            resp_json = self._create_account(credentials, message_uid, integration_service)
        except (AgentError, JoinError) as ex:
            self._log_audit_response(ex.response, message_uid, integration_service)
            self.audit_logger.send_to_atlas()
            if ex.response.status_code not in HANDLED_STATUS_CODES:
                ex.response.status_code = "UNKNOWN"
            self.handle_errors(ex.response.status_code)

        self.identifier = {
            "merchant_identifier": resp_json["UserId"],
            "card_number": resp_json["MembershipNumber"],
        }
        self.user_info["credentials"].update(self.identifier)
        try:
            self._update_newsletters(resp_json["UserId"], consents)
        except (AgentError, JoinError):
            pass

    def login(self, credentials):
        # SM is not supposed to use login as part of the JOIN journey
        if self.journey_type == "JOIN":
            return
        try:
            self._login(credentials)
        except (JoinError, AgentError) as ex:
            if ex.response.status_code not in HANDLED_STATUS_CODES:
                ex.response.status_code = "UNKNOWN"
            self.handle_errors(ex.response.status_code)

    def scrape_transactions(self):
        return self.point_transactions

    def parse_transaction(self, transaction: dict):
        return Transaction(
            date=transaction["ConfirmedDate"],
            points=Decimal(transaction["AwardedPoints"]),
            description=transaction["EarnReason"],
        )

    def balance(self):
        try:
            points_data = self._get_balance()
        except (JoinError, AgentError) as ex:
            if ex.response.status_code not in HANDLED_STATUS_CODES:
                ex.response.status_code = "UNKNOWN"
            self.handle_errors(ex.response.status_code)

        self.point_transactions = points_data["PointsActivity"]

        return Balance(
            points=Decimal(points_data["TotalPoints"]),
            value=0,
            value_label="",
            reward_tier=points_data["LoyaltyTier"],
        )
