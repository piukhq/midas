import json
from decimal import Decimal
from typing import Optional

import arrow
import requests
import sentry_sdk
from blinker import signal
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential
from user_auth_token import UserTokenStore

import settings
from app import publish
from app.agents.base import ApiMiner, Balance, check_correct_authentication
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    CARD_NOT_REGISTERED,
    CARD_NUMBER_ERROR,
    CONFIGURATION_ERROR,
    GENERAL_ERROR,
    JOIN_ERROR,
    JOIN_IN_PROGRESS,
    LINK_LIMIT_EXCEEDED,
    NO_SUCH_RECORD,
    NOT_SENT,
    PRE_REGISTERED_CARD,
    SERVICE_CONNECTION_ERROR,
    STATUS_LOGIN_FAILED,
    UNKNOWN,
    AgentError,
    JoinError,
    LoginError,
)
from app.agents.schemas import Transaction
from app.encryption import hash_ids
from app.exceptions import AgentException
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.tasks.resend_consents import ConsentStatus

RETRY_LIMIT = 3
log = get_logger("iceland")


JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING = {
    JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
    JourneyTypes.LINK: Configuration.VALIDATE_HANDLER,
    JourneyTypes.ADD: Configuration.VALIDATE_HANDLER,
    JourneyTypes.UPDATE: Configuration.UPDATE_HANDLER,
}


class Iceland(ApiMiner):
    token_store = UserTokenStore(settings.REDIS_URL)
    AUTH_TOKEN_TIMEOUT = 3599

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.config = config or Configuration(
            scheme_slug,
            handler_type,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.security_credentials = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self._balance_amount = None
        self._transactions = None
        self.errors = {
            ACCOUNT_ALREADY_EXISTS: ["ALREADY_PROCESSED", "ACCOUNT_ALREADY_EXISTS"],
            CARD_NOT_REGISTERED: "CARD_NOT_REGISTERED",
            CARD_NUMBER_ERROR: "CARD_NUMBER_ERROR",
            GENERAL_ERROR: "GENERAL_ERROR",
            JOIN_ERROR: "JOIN_ERROR",
            JOIN_IN_PROGRESS: "JOIN_IN_PROGRESS",
            LINK_LIMIT_EXCEEDED: "LINK_LIMIT_EXCEEDED",
            NO_SUCH_RECORD: "NO_SUCH_RECORD",
            NOT_SENT: "NOT_SENT",
            PRE_REGISTERED_CARD: "PRE_REGISTERED_ERROR",
            STATUS_LOGIN_FAILED: "VALIDATION",
            UNKNOWN: "UNKNOWN",
        }

    def add_additional_consent(self) -> None:
        if len(self.user_info["credentials"]["consents"]) < 2:
            journey_type = self.user_info["credentials"]["consents"][0]["journey_type"]
            consent = {
                "id": 99999999999,
                "slug": "marketing_opt_in_thirdparty",
                "value": False,
                "created_on": arrow.now().isoformat(),  # '2020-05-26T15:30:16.096802+00:00',
                "journey_type": journey_type,
            }
            self.user_info["credentials"]["consents"].append(consent)
        else:
            log.debug("Too many consents for Iceland scheme.")

    def create_join_request_payload(self) -> dict:
        credentials = self.user_info["credentials"]
        marketing_mapping = {i["slug"]: i["value"] for i in credentials["consents"]}
        return {
            "town_city": credentials["town_city"],
            "county": credentials["county"],
            "title": credentials["title"],
            "address_1": credentials["address_1"],
            "first_name": credentials["first_name"],
            "last_name": credentials["last_name"],
            "email": credentials["email"],
            "postcode": credentials["postcode"],
            "address_2": credentials["address_2"],
            "record_uid": self.record_uid,
            "country": self.config.country,
            "message_uid": self.message_uid,
            "callback_url": self.config.callback_url,
            "marketing_opt_in": marketing_mapping.get("marketing_opt_in"),
            "marketing_opt_in_thirdparty": marketing_mapping.get("marketing_opt_in_thirdparty"),
            "merchant_scheme_id1": hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0]),
            "dob": credentials["date_of_birth"],
            "phone1": credentials["phone"],
        }

    def _process_join_callback_response(self, data):
        signal("send-audit-response").send(
            response=json.dumps(data),
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            scheme_slug=self.scheme_slug,
            handler_type=self.config.handler_type[0],
            integration_service=self.integration_service,
            status_code=0,  # Doesn't have a status code since this is an async response
            channel=self.channel,
        )
        consent_status = ConsentStatus.PENDING
        try:
            error = data.get("error_codes")
            if error:
                self.handle_errors(error_code=error[0]["code"], exception_type=JoinError)
            update_pending_join_account(self.user_info, "success", self.message_uid, identifier=self.identifier)
            consent_status = ConsentStatus.SUCCESS
        except (AgentException, LoginError, JoinError, AgentError):
            consent_status = ConsentStatus.FAILED
            raise
        finally:
            self.consent_confirmation(self.user_info["credentials"].get("consents", []), consent_status)

        status = SchemeAccountStatus.ACTIVE
        publish.status(self.scheme_id, status, self.message_uid, self.user_info, journey="join")

    def join_callback(self, data: dict) -> None:
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        self.identifier = {
            "barcode": data.get("barcode"),  # type:ignore
            "card_number": data.get("card_number"),  # type:ignore
            "merchant_identifier": data.get("merchant_scheme_id2"),  # type:ignore
        }
        self.message_uid = data["message_uid"]
        try:
            self._process_join_callback_response(data)
            signal("callback-success").send(self, slug=self.scheme_slug)
        except AgentError as e:
            signal("callback-fail").send(self, slug=self.scheme_slug)
            update_pending_join_account(self.user_info, e.args[0], self.message_uid, raise_exception=False)
            raise
        except (AgentException, LoginError):
            signal("callback-fail").send(self, slug=self.scheme_slug)
            raise

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _join(self, payload: dict):
        try:
            response = self.make_request(self.config.merchant_url, method="post", audit=True, json=payload)
            if response.text == "":
                return {}
            return response.json()
        except (JoinError, AgentError) as e:
            signal("join-fail").send(self, slug=self.scheme_slug)
            self.handle_errors(e.name)

    def join(self, data: dict) -> None:
        # Barclays expects only 1 consent for an Iceland join, whereas Iceland expects 2
        # Save the current consent to a variable for use in self.consent_confirmation below
        consents = self.user_info["credentials"].get("consents", []).copy()
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.ASYNC_INTEGRATION][1].upper()
        self.expecting_callback = True
        # Add the additional consent for Iceland
        if consents:
            self.add_additional_consent()

        response_json = self._join(self.create_join_request_payload())

        error = response_json.get("error_codes")
        if error:
            consent_status = ConsentStatus.FAILED
            self.consent_confirmation(consents, consent_status)
            self.handle_errors(error[0]["code"], exception_type=JoinError)

        consent_status = ConsentStatus.PENDING
        self.consent_confirmation(consents, consent_status)

    def _authenticate(self) -> str:
        have_valid_token = False
        current_timestamp = (arrow.utcnow().int_timestamp,)
        token = ""
        try:
            cached_token = json.loads(self.token_store.get(self.scheme_id))
            try:
                if self._token_is_valid(cached_token, current_timestamp):
                    have_valid_token = True
                    token = cached_token["iceland_access_token"]
            except (KeyError, TypeError) as e:
                log.exception(e)
        except (KeyError, self.token_store.NoSuchToken):
            pass

        if not have_valid_token:
            token = self._refresh_token()
            self._store_token(token, current_timestamp)

        self.headers["Authorization"] = f"Bearer {token}"

        return token

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _refresh_token(self) -> str:
        url = self.security_credentials["url"]
        payload = {
            "grant_type": "client_credentials",
            "client_secret": self.security_credentials["payload"]["client_secret"],
            "client_id": self.security_credentials["payload"]["client_id"],
            "resource": self.security_credentials["payload"]["resource"],
        }

        try:
            response = requests.post(url, data=payload)
        except requests.RequestException as e:
            sentry_sdk.capture_message(f"Failed request to get oauth token from {url}. exception: {e}")
            raise AgentError(SERVICE_CONNECTION_ERROR) from e
        except (KeyError, IndexError) as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        return response.json()["access_token"]

    def _store_token(self, token: str, current_timestamp: tuple[int]) -> None:
        token_dict = {
            "iceland_access_token": token,
            "timestamp": current_timestamp,
        }
        self.token_store.set(scheme_account_id=self.scheme_id, token=json.dumps(token_dict))

    def _token_is_valid(self, token: dict, current_timestamp: tuple[int]) -> bool:
        time_diff = current_timestamp[0] - token["timestamp"][0]
        return time_diff < self.AUTH_TOKEN_TIMEOUT

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _login(self, payload: dict):
        try:
            response = self.make_request(url=self.config.merchant_url, method="post", audit=True, json=payload)
            return response.json()
        except (LoginError, AgentError) as e:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            self.handle_errors(e.name)

    def login(self, credentials) -> None:
        self.integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()
        authentication_service = self.config.security_credentials["outbound"]["service"]
        check_correct_authentication(
            actual_config_auth_type=authentication_service,
            allowed_config_auth_types=[Configuration.OPEN_AUTH_SECURITY, Configuration.OAUTH_SECURITY],
        )
        if authentication_service == Configuration.OAUTH_SECURITY:
            self._authenticate()
        payload = {
            "card_number": credentials["card_number"],
            "last_name": credentials["last_name"],
            "postcode": credentials["postcode"],
            "message_uid": self.message_uid,
            "record_uid": self.record_uid,
            "callback_url": self.config.callback_url,
            "merchant_scheme_id1": hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0]),
            "merchant_scheme_id2": credentials.get("merchant_identifier"),
        }

        response_json = self._login(payload)

        error = response_json.get("error_codes")
        if error:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            self.handle_errors(error[0]["code"])
        else:
            signal("log-in-success").send(self, slug=self.scheme_slug)

        if not self.identifier:
            self.identifier = {
                "barcode": response_json.get("barcode"),
                "card_number": response_json.get("card_number"),
                "merchant_identifier": response_json.get("merchant_scheme_id2"),
            }
        self.user_info["credentials"].update(self.identifier)

        self._balance_amount = response_json["balance"]
        self._transactions = response_json.get("transactions")

    def balance(self) -> Optional[Balance]:
        amount = Decimal(self._balance_amount).quantize(TWO_PLACES)
        return Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )

    def transactions(self) -> list[Transaction]:
        if self._transactions is None:
            return []
        try:
            return self.hash_transactions(self.transaction_history())
        except Exception:
            return []

    def transaction_history(self) -> list[Transaction]:
        return [self.parse_transaction(tx) for tx in self._transactions]

    def parse_transaction(self, row: dict) -> Transaction:
        return Transaction(
            date=arrow.get(row["timestamp"]),
            description=row["reference"],
            points=Decimal(row["value"]),
        )
