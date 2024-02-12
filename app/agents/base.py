import hashlib
import json
import time
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from typing import Any, Optional
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit, urljoin
from uuid import uuid4

import arrow
import requests
import sentry_sdk
from blinker import signal
from requests import HTTPError, Response
from requests.exceptions import ConnectionError, RetryError
from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.agents.schemas import Balance, Transaction
from app.encryption import hash_ids
from app.exceptions import (
    AccountAlreadyExistsError,
    BaseError,
    ConfigurationError,
    EndSiteDownError,
    IPBlockedError,
    JoinError,
    NotSentError,
    PreRegisteredCardError,
    ResourceNotFoundError,
    RetryLimitReachedError,
    ServiceConnectionError,
    StatusLoginFailedError,
    UnknownError,
)
from app.mocks.users import USER_STORE
from app.reporting import get_logger
from app.requests_retry import requests_retry_session
from app.scheme_account import TWO_PLACES, JourneyTypes
from app.tasks.resend_consents import send_consent_status

log = get_logger("agent-base")


JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING = {
    JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
    JourneyTypes.LINK: Configuration.VALIDATE_HANDLER,
    JourneyTypes.ADD: Configuration.VALIDATE_HANDLER,
    JourneyTypes.UPDATE: Configuration.UPDATE_HANDLER,
    JourneyTypes.REMOVED: Configuration.REMOVED_HANDLER,
}


class BaseAgent(object):
    retry_limit: Optional[int] = 5
    point_conversion_rate = Decimal("0")
    identifier_type: Optional[list[str]] = None
    identifier: Optional[dict[str, str]] = None
    expecting_callback = False
    is_async = False
    create_journey: Optional[str] = None

    def __init__(
        self,
        retry_count: int,
        user_info: dict,
        config_handler_type: int,
        scheme_slug: str,
        config: Configuration | None = None,
    ):
        self.config = config or Configuration(
            scheme_slug,
            config_handler_type,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
            settings.AZURE_AAD_TENANT_ID,
        )
        self.audit_handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.retry_count = retry_count
        self.user_info = user_info
        self.scheme_slug = scheme_slug

        self.scheme_id = self.user_info["scheme_account_id"]
        self.channel = self.user_info.get("channel", "")
        self.journey_type = self.user_info.get("journey_type")

        self.record_uid = hash_ids.encode(self.scheme_id)
        self.message_uid = str(uuid4())
        self.max_retries = 3
        self.token_store = UserTokenStore(settings.REDIS_URL)
        self.oauth_token_timeout: int = 0

        self.session = requests_retry_session(retries=self.max_retries)
        self.headers: dict[str, str] = {}
        self.errors: dict[type[BaseError], list[int]] = {}
        self.integration_service = ""
        self.outbound_auth_service: int = Configuration.OAUTH_SECURITY
        self.audit_config: dict[str, Any] = {}

        if settings.SENTRY_DSN:
            sentry_sdk.set_tag("scheme_slug", self.scheme_slug)

    def send_audit_request(self, payload: dict, url: str) -> None:
        audit_payload = deepcopy(payload)
        if audit_payload.get("password"):
            audit_payload["password"] = "REDACTED"

        audit_payload["url"] = url
        signal("send-audit-request").send(
            self,
            payload=audit_payload,
            scheme_slug=self.scheme_slug,
            handler_type=self.audit_handler_type,
            integration_service=self.integration_service,
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            channel=self.channel,
            audit_config=self.audit_config,
        )

    def send_audit_response(self, response: Response) -> None:
        signal("send-audit-response").send(
            self,
            response=response,
            scheme_slug=self.scheme_slug,
            handler_type=self.audit_handler_type,
            integration_service=self.integration_service,
            status_code=response.status_code,
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            channel=self.channel,
            audit_config=self.audit_config,
        )

    @staticmethod
    def get_audit_payload(kwargs, url) -> dict:
        """
        Instead of changing Atlas and releasing 2 repos make agent
        modifications by overriding this method. Ensure you don't
        send None in string fields which Atlas exceptions e.g. email
        """
        if "json" in kwargs:
            return kwargs["json"]
        elif "data" in kwargs:
            data = kwargs["data"]
            if isinstance(data, dict):
                return data
            else:
                return json.loads(data)
        else:
            data = urlsplit(url).query
            return {k: v[0] if len(v) == 1 else v for k, v in parse_qs(data).items()}

    def authenticate(self):
        if self.outbound_auth_service == Configuration.OPEN_AUTH_SECURITY:
            return
        if self.outbound_auth_service == Configuration.OAUTH_SECURITY:
            self._oauth_authentication()

    def get_auth_url_and_payload(self):
        raise NotImplementedError()

    def _oauth_authentication(self):
        have_valid_token = False
        current_timestamp = arrow.utcnow().int_timestamp
        token = ""
        try:
            cached_token = json.loads(self.token_store.get(self.scheme_id))
            try:
                if self._token_is_valid(cached_token, current_timestamp):
                    have_valid_token = True
                    token = cached_token[f"{self.scheme_slug.replace('-', '_')}_access_token"]
            except (KeyError, TypeError) as e:
                log.exception(e)
        except (KeyError, self.token_store.NoSuchToken):
            pass

        if not have_valid_token:
            token = self._refresh_token()
            self._store_token(token, current_timestamp)

        self.headers["Authorization"] = f"Bearer {token}"

    def _refresh_token(self) -> str:
        url, payload = self.get_auth_url_and_payload()
        try:
            response = self.session.post(url, data=payload, headers=self.headers)
        except requests.RequestException as e:
            sentry_sdk.capture_message(f"Failed request to get oauth token from {url}. exception: {e}")
            raise ServiceConnectionError(exception=e) from e
        except (KeyError, IndexError) as e:
            raise ConfigurationError(exception=e) from e

        return response.json()["access_token"]

    def _store_token(self, token: str, current_timestamp: int) -> None:
        token_dict = {
            f"{self.scheme_slug.replace('-', '_')}_access_token": token,
            "timestamp": current_timestamp,
        }
        self.token_store.set(scheme_account_id=self.scheme_id, token=json.dumps(token_dict))

    def _token_is_valid(self, token: dict, current_timestamp: int) -> bool:
        if isinstance(token["timestamp"], list):
            token_timestamp = token["timestamp"][0]
        else:
            token_timestamp = token["timestamp"]

        return current_timestamp - token_timestamp < self.oauth_token_timeout

    def _remove_unique_data_in_path(self, endpoint: str, unique_data: str) -> str:
        path_list = endpoint.split("/")

        for i in range(len(path_list)):
            if path_list[i] == unique_data:
                path_list[i] = "unique-data"

        return "/".join(path_list)

    def make_request(self, url, unique_data=None, method="get", timeout=5, audit=False, **kwargs):
        # Combine the passed kwargs with our headers and timeout values.
        path = urlsplit(url).path  # Get the path part of the url for signal call
        args = {
            "headers": self.headers,
            "timeout": timeout,
        }
        args.update(kwargs)

        # Prevent audit logging when agent login method is called for update
        if self.journey_type is JourneyTypes.UPDATE:
            audit = False

        try:
            if audit:
                audit_payload = self.get_audit_payload(kwargs, url)
                self.send_audit_request(audit_payload, url)

            resp = self.session.request(method, url=url, **args)

            if audit:
                self.send_audit_response(resp)

        except RetryError as e:
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=RetryLimitReachedError)
            raise RetryLimitReachedError(exception=e) from e

        except ConnectionError as e:
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=EndSiteDownError)
            raise EndSiteDownError(exception=e) from e

        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=self._remove_unique_data_in_path(path, unique_data) if unique_data else path,
            latency=resp.elapsed.total_seconds(),
            response_code=resp.status_code,
        )

        resp = self.check_response_for_errors(resp)
        return resp

    def check_response_for_errors(self, resp):
        try:
            resp.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 401:
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=StatusLoginFailedError,
                )
                raise StatusLoginFailedError(exception=e)
            elif e.response.status_code == 403:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=IPBlockedError)
                raise IPBlockedError(exception=e) from e
            elif e.response.status_code == 404:
                signal("request-fail").send(
                    self, slug=self.scheme_slug, channel=self.channel, error=ResourceNotFoundError
                )
                raise ResourceNotFoundError(exception=e) from e
            elif e.response.status_code in [503, 504]:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=NotSentError)
                raise NotSentError(exception=e) from e
            else:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=EndSiteDownError)
                raise EndSiteDownError(exception=e) from e

        return resp

    def handle_error_codes(self, error_code, unhandled_exception=UnknownError):
        for agent_error, agent_error_codes in self.errors.items():
            if error_code in agent_error_codes:
                raise agent_error
        raise unhandled_exception

    def update_hermes_credentials(self) -> None:
        api_url = urljoin(
            settings.HERMES_URL,
            f"schemes/accounts/{self.user_info['scheme_account_id']}/credentials",
        )
        headers = {
            "Content-type": "application/json",
            "Authorization": "token " + settings.SERVICE_API_KEY,
            "bink-user-id": str(self.user_info["bink_user_id"]),
        }
        requests.put(  # Don't want to call any signals for internal calls
            api_url, data=json.dumps(self.identifier), headers=headers
        )

    def join(self):
        raise NotImplementedError()

    def login(self):
        raise NotImplementedError()

    def balance(self) -> Optional[Balance]:
        raise NotImplementedError()

    def transactions(self) -> list[Transaction]:
        raise NotImplementedError()

    def calculate_label(self, points: Decimal) -> str:
        raise NotImplementedError()

    def loyalty_card_removed(self) -> None:
        """
        When a card is removed from bink and the agent must report it override this function
        - requires the JourneyTypes.REMOVED will be passed in user info and the agent must pass
        the journey types to the base class init and not pre-set it. Europa must be configured
        for Configuration.REMOVED_HANDLER
        """
        raise NotImplementedError()

    def hash_transactions(self, transactions: list[Transaction]) -> list[Transaction]:
        count: defaultdict[str, int] = defaultdict(int)

        hashed_transactions: list[Transaction] = []

        for transaction in transactions:
            s = "{0}{1}{2}{3}{4}".format(
                transaction.date,
                transaction.description,
                transaction.points,
                self.scheme_id,
                transaction.location if transaction.location is not None else "",
            )

            # identical hashes get sequentially indexed to make them unique.
            index = count[s]
            count[s] += 1
            s = "{0}{1}".format(s, index)

            data = transaction._asdict()
            data["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()
            hashed_transactions.append(Transaction(**data))

        return hashed_transactions

    def calculate_point_value(self, points: Decimal) -> Decimal:
        return (points * self.point_conversion_rate).quantize(TWO_PLACES)

    def account_overview(self) -> dict:
        return {"balance": self.balance(), "transactions": self.transactions()}

    @staticmethod
    def format_label(count, noun, plural_suffix="s", include_zero_items=False):
        if count == 0 and not include_zero_items:
            return ""
        return "{} {}".format(count, noun + pluralise(count, plural_suffix))

    # Expects a list of tuples (point threshold, reward string) sorted by threshold from highest to lowest.
    @staticmethod
    def calculate_tiered_reward(points, reward_tiers):
        for threshold, reward in reward_tiers:
            if points >= threshold:
                return reward
        return ""

    @staticmethod
    def update_questions(questions):
        return questions

    def attempt_login(self):
        if self.retry_limit and self.retry_count >= self.retry_limit:
            raise RetryLimitReachedError()

        try:
            self.login()
        except KeyError as e:
            raise Exception(f"missing the credential '{e.args[0]}'")

    def attempt_join(self):
        try:
            self.join()
        except KeyError as e:
            raise Exception(f"missing the credential '{e.args[0]}'")

    @staticmethod
    def consent_confirmation(consents_data: list[dict], status: int) -> None:
        """
        Packages the consent data into another dictionary, with retry information and status, and sends to hermes.

        :param consents_data: list of dicts.
        [{
            'id': int. UserConsent id. (Required)
            'slug': string. Consent slug.
            'value': bool. User's consent decision. (Required)
            'created_on': string. Datetime string of when the UserConsent instance was created.
            'journey_type': int. Usually of JourneyTypes IntEnum.
        }]
        :param status: int. Should be of type ConsentStatus.
        :return: None
        """
        confirm_tries = {}
        for consent in consents_data:
            confirm_tries[consent["id"]] = settings.HERMES_CONFIRMATION_TRIES

        retry_data = {"confirm_tries": confirm_tries, "status": status}

        send_consent_status(retry_data)


def pluralise(count, plural_suffix):
    if "," not in plural_suffix:
        plural_suffix = "," + plural_suffix
    parts = plural_suffix.split(",")
    if len(parts) > 2:
        return ""
    singular, plural = parts[:2]
    return singular if count == 1 else plural


def check_correct_authentication(allowed_config_auth_types: list[int], actual_config_auth_type: int) -> None:
    if actual_config_auth_type not in allowed_config_auth_types:
        raise ConfigurationError(
            message=f"Agent expecting Security Type(s) "
            f"{[Configuration.SECURITY_TYPE_CHOICES[i][1] for i in allowed_config_auth_types]} but got "
            f"Security Type '{Configuration.SECURITY_TYPE_CHOICES[actual_config_auth_type][1]}' instead",
        )


def create_error_response(error_code, error_description):
    response_json = json.dumps({"error_codes": [{"code": error_code, "description": error_description}]})

    return response_json


class MockedMiner(BaseAgent):
    add_error_credentials: dict[str, dict[str, type[BaseError]]] = {}
    existing_card_numbers: dict[str, str] = {}
    ghost_card_prefix: Optional[str] = None
    join_fields: set[str] = set()
    join_prefix = "1"
    retry_limit = None
    titles: list[str] = []

    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = MagicMock()
        super().__init__(retry_count, user_info, config_handler_type=None, scheme_slug=scheme_slug, config=config)
        self.errors = {}
        self.headers = {}
        self.identifier = {}
        self.retry_count = retry_count
        self.scheme_slug = scheme_slug
        self.user_info = user_info
        self.journey_type = self.user_info.get("journey_type")
        self.credentials = self.user_info["credentials"]
        self.scheme_id = user_info["scheme_account_id"]

    def check_and_raise_error_credentials(self):
        for credential_type, credential in self.credentials.items():
            try:
                error_to_raise = self.add_error_credentials[credential_type][credential]
                raise error_to_raise
            except KeyError:
                pass

        card_number = self.credentials.get("card_number") or self.credentials.get("barcode")
        if self.ghost_card_prefix and card_number and card_number.startswith(self.ghost_card_prefix):
            raise PreRegisteredCardError()

    @staticmethod
    def _check_email_already_exists(email):
        return any(info["credentials"].get("email") == email for info in USER_STORE.values())

    def _check_existing_join_credentials(self, email, ghost_card):
        if ghost_card:
            if ghost_card in self.existing_card_numbers:
                raise AccountAlreadyExistsError()
            if self._check_email_already_exists(email):
                raise JoinError()
        else:
            if self._check_email_already_exists(email):
                raise AccountAlreadyExistsError()

    def _validate_join_credentials(self, data):
        for join_field in self.join_fields:
            if join_field not in data.keys():
                raise KeyError(join_field)

        email = data.get("email").lower()
        ghost_card = data.get("card_number") or data.get("barcode")
        self._check_existing_join_credentials(email, ghost_card)

        if email == "fail@unknown.com":
            raise UnknownError()
        elif email == "slowjoin@testbink.com":
            time.sleep(60)

        title = data.get("title").capitalize()
        if self.titles and title not in self.titles:
            raise JoinError()

        return {"message": "success"}
