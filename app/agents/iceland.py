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
from app.agents.base import ApiMiner, Balance, check_correct_authentication
from app.agents.exceptions import (
    CARD_NOT_REGISTERED,
    CARD_NUMBER_ERROR,
    CONFIGURATION_ERROR,
    GENERAL_ERROR,
    LINK_LIMIT_EXCEEDED,
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
from app.publish import thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes, update_pending_join_account, SchemeAccountStatus
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
            STATUS_LOGIN_FAILED: "VALIDATION",
            CARD_NUMBER_ERROR: "CARD_NUMBER_ERROR",
            LINK_LIMIT_EXCEEDED: "LINK_LIMIT_EXCEEDED",
            CARD_NOT_REGISTERED: "CARD_NOT_REGISTERED",
            GENERAL_ERROR: "GENERAL_ERROR",
        }
        self.integration_service = self.config.integration_service

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

        self.identifier = {
            "barcode": response_json.get("barcode"),
            "card_number": response_json.get("card_number"),
            "merchant_identifier": response_json.get("merchant_scheme_id2"),
        }
        self.user_info["credentials"].update(self.identifier)

        self._balance_amount = response_json["balance"]
        self._transactions = response_json.get("transactions")

    def _check_for_error_response(self, response):
        error = None
        for key in self.ERRORS_KEYS:
            error = response.get(key)
            if error:
                break
        return error

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

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _join(self, payload: dict) -> dict:
        self.make_request(self.config.merchant_url, method="post", json=payload)

    def join(self, credentials: dict, inbound=False) -> None:
        # marketing_opt_in_thirdparty not to be included in consent_confirmation function called below
        consents = self.user_info["credentials"].get("consents", []).copy()
        if inbound:
            self.record_uid = hash_ids.encode(self.scheme_id)
            thread_pool_executor.submit(self._inbound_handler, credentials, self.scheme_slug)
        if consents:
            if len(consents) < 2:
                journey_type = consents[0]["journey_type"]
                consent = {
                    "id": 99999999999,
                    "slug": "marketing_opt_in_thirdparty",
                    "value": False,
                    "created_on": arrow.now().isoformat(),  # '2020-05-26T15:30:16.096802+00:00',
                    "journey_type": journey_type,
                }
                credentials["consents"].append(consent)
            else:
                log.debug("Too many consents for Iceland scheme.")
        marketing_mapping = {i["slug"]: i["value"] for i in credentials["consents"]}

        payload = {
            "town_city": credentials["town_city"],
            "county": credentials["county"],
            "title": credentials["title"],
            "address_1": credentials["address_1"],
            "first_name": credentials["first_name"],
            "last_name": credentials["last_name"],
            "email": credentials["email"],
            "postcode": credentials["postcode"],
            "address_2": credentials["address_2"],
            "record_uid": hash_ids.encode(self.scheme_id),
            "country": self.config.country,
            "message_uid": str(uuid4()),
            "callback_url": self.config.callback_url,
            "marketing_opt_in": marketing_mapping["marketing_opt_in"],
            "marketing_opt_in_thirdparty": marketing_mapping["marketing_opt_in_thirdparty"],
            "merchant_scheme_id1": hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0]),
            "dob": credentials["date_of_birth"],
            "phone1": credentials["phone"],
        }

        async_service_identifier = Configuration.INTEGRATION_CHOICES[Configuration.ASYNC_INTEGRATION][1].upper()
        if self.config.integration_service == async_service_identifier:
            self.expecting_callback = True

        self._join(payload)

        consent_status = ConsentStatus.PENDING
        self.consent_confirmation(consents, consent_status)

    def _create_log_message(
        self,
        json_msg,
        msg_uid,
        scheme_slug,
        handler_type,
        integration_service,
        direction,
        contains_errors=False,
    ):
        return {
            "json": json_msg,
            "message_uid": msg_uid,
            "record_uid": self.record_uid,
            "merchant_id": scheme_slug,
            "handler_type": handler_type,
            "integration_service": integration_service,
            "direction": direction,
            "expiry_date": arrow.utcnow().shift(days=+90).format("YYYY-MM-DD HH:mm:ss"),
            "contains_errors": contains_errors,
        }

    # Should be overridden in the agent if there is agent specific processing required for their response.
    def process_join_response(self):
        """
        Processes a merchant's response to a join request. On success, sets scheme account as ACTIVE and adds
        identifiers/scheme credential answers to database.
        :return: None
        """
        consent_status = ConsentStatus.PENDING
        try:
            error = self._check_for_error_response(self.result)
            if error:
                self.handle_errors(error[0]["code"], exception_type=JoinError)

            identifier = self._get_identifiers(self.result)
            update_pending_join_account(self.user_info, "success", self.message_uid, identifier=identifier)
            consent_status = ConsentStatus.SUCCESS

        except (AgentException, LoginError, AgentError):
            consent_status = ConsentStatus.FAILED
            raise
        finally:
            self.consent_confirmation(self.consents_data, consent_status)

        status = SchemeAccountStatus.ACTIVE
        publish.status(self.scheme_id, status, self.message_uid, self.user_info, journey="join")

    def _inbound_handler(self, data, scheme_slug):
        """
        Handler service for inbound response i.e. response from async join. The response json is logged,
        converted to a python object and passed to the relevant method for processing.
        :param data: dict of payload
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :return: dict of response data
        """
        self.result = data
        self.message_uid = self.result.get("message_uid")

        logging_info = self._create_log_message(
            data,
            self.message_uid,
            scheme_slug,
            self.config.handler_type,
            "ASYNC",
            "INBOUND",
        )

        signal("send-audit-response").send(
            response=json.dumps(data),
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            scheme_slug=self.scheme_slug,
            handler_type=self.config.handler_type[0],
            integration_service=self.config.integration_service,
            status_code=0,  # Doesn't have a status code since this is an async response
            channel=self.channel,
        )

        if self._check_for_error_response(self.result):
            logging_info["contains_errors"] = True
            log.warning(json.dumps(logging_info))
        else:
            log.info(json.dumps(logging_info))

        try:
            response = self.process_join_response()
            signal("callback-success").send(self, slug=self.scheme_slug)
        except AgentError as e:
            signal("callback-fail").send(self, slug=self.scheme_slug)
            update_pending_join_account(self.user_info, e.args[0], self.message_uid, raise_exception=False)
            raise
        except (AgentException, LoginError):
            signal("callback-fail").send(self, slug=self.scheme_slug)
            raise

        return response
