import hashlib
import json
import time
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from typing import Optional
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import sentry_sdk
from blinker import signal
from requests import HTTPError
from requests.exceptions import RetryError, Timeout
from soteria.configuration import Configuration

import settings
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    CONFIGURATION_ERROR,
    END_SITE_DOWN,
    IP_BLOCKED,
    JOIN_ERROR,
    NOT_SENT,
    PRE_REGISTERED_CARD,
    RETRY_LIMIT_REACHED,
    STATUS_LOGIN_FAILED,
    UNKNOWN,
    AgentError,
    JoinError,
    LoginError,
    RetryLimitError,
)
from app.agents.schemas import Balance, Transaction
from app.encryption import hash_ids
from app.mocks.users import USER_STORE
from app.publish import thread_pool_executor
from app.reporting import LOGGING_SENSITIVE_KEYS, get_logger, sanitise
from app.requests_retry import requests_retry_session
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import get_security_agent
from app.tasks.resend_consents import ConsentStatus, send_consent_status
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes
from app.tasks.resend_consents import send_consent_status

log = get_logger("agent-base")


class BaseAgent(object):
    retry_limit: Optional[int] = 2
    point_conversion_rate = Decimal("0")
    connect_timeout = 3
    known_captcha_signatures = [
        "recaptcha",
        "captcha",
        "Incapsula",
    ]
    identifier_type: Optional[list[str]] = None
    identifier: Optional[dict[str, str]] = None
    expecting_callback = False
    is_async = False
    create_journey: Optional[str] = None

    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.scheme_id = user_info["scheme_account_id"]
        self.scheme_slug = scheme_slug
        self.account_status = user_info["status"]
        self.journey_type = user_info.get("journey_type")
        self.headers = {}
        self.retry_count = retry_count
        self.errors = {}
        self.user_info = user_info
        self.channel = user_info.get("channel", "")
        self.audit_handlers = {
            JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
            JourneyTypes.ADD: Configuration.VALIDATE_HANDLER,
            JourneyTypes.LINK: Configuration.VALIDATE_HANDLER,
        }
        self.record_uid = hash_ids.encode(self.scheme_id)
        self.message_uid = str(uuid4())
        self.integration_service = None
        self.max_retries = 3
        self.session = requests_retry_session(retries=self.max_retries)

    def send_audit_request(self, payload, handler_type):
        audit_payload = deepcopy(payload)
        if audit_payload.get("password"):
            audit_payload["password"] = "REDACTED"

        signal("send-audit-request").send(
            self,
            payload=audit_payload,
            scheme_slug=self.scheme_slug,
            handler_type=handler_type,
            integration_service=self.integration_service,
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            channel=self.channel,
        )

    def send_audit_response(self, response, handler_type):
        signal("send-audit-response").send(
            self,
            response=response,
            scheme_slug=self.scheme_slug,
            handler_type=handler_type,
            integration_service=self.integration_service,
            status_code=response.status_code,
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            channel=self.channel,
        )

    @staticmethod
    def _get_audit_payload(kwargs, url):
        if "json" in kwargs or "data" in kwargs:
            return kwargs["json"] if kwargs.get("json") else kwargs["data"]
        else:
            data = urlsplit(url).query
            return {k: v[0] if len(v) == 1 else v for k, v in parse_qs(data).items()}

    def make_request(self, url, method="get", timeout=5, audit=False, **kwargs):
        # Combine the passed kwargs with our headers and timeout values.
        path = urlsplit(url).path  # Get the path part of the url for signal call
        args = {
            "headers": self.headers,
            "timeout": timeout,
        }
        args.update(kwargs)

        # Prevent audit logging when agent login method is called for update
        if self.journey_type not in self.audit_handlers.keys():
            audit = False

        try:
            if audit:
                audit_payload = self._get_audit_payload(kwargs, url)
                handler_type = self.audit_handlers[self.journey_type]
                self.send_audit_request(audit_payload, handler_type)

            resp = self.session.request(method, url=url, **args)

            if audit:
                self.send_audit_response(resp, handler_type)

        except Timeout as exception:
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error="Timeout")
            sentry_sdk.capture_exception(exception)
            raise AgentError(END_SITE_DOWN) from exception

        except RetryError as exception:
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=RETRY_LIMIT_REACHED)
            sentry_sdk.capture_exception(exception)
            raise AgentError(RETRY_LIMIT_REACHED) from exception

        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=path,
            latency=resp.elapsed.total_seconds(),
            response_code=resp.status_code,
        )

        try:
            resp.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 401:
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.channel,
                    error=STATUS_LOGIN_FAILED,
                )
                raise LoginError(STATUS_LOGIN_FAILED, response=e.response)
            elif e.response.status_code == 403:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=IP_BLOCKED)
                raise AgentError(IP_BLOCKED, response=e.response) from e
            elif e.response.status_code in [503, 504]:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=NOT_SENT)
                raise AgentError(NOT_SENT, response=e.response) from e
            else:
                signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=END_SITE_DOWN)
                raise AgentError(END_SITE_DOWN, response=e.response) from e

        return resp

    def handle_errors(self, error_code, exception_type=LoginError, unhandled_exception_code=UNKNOWN):
        for key, values in self.errors.items():
            if error_code in values:
                raise exception_type(key)
        raise AgentError(unhandled_exception_code)

    def join(self, credentials):
        raise NotImplementedError()

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self) -> Optional[Balance]:
        raise NotImplementedError()

    def transactions(self) -> list[Transaction]:
        raise NotImplementedError()

    def calculate_label(self, points: Decimal) -> str:
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

    def attempt_login(self, credentials):
        if self.retry_limit and self.retry_count >= self.retry_limit:
            raise RetryLimitError(RETRY_LIMIT_REACHED)

        try:
            self.login(credentials)
        except KeyError as e:
            raise Exception("missing the credential '{0}'".format(e.args[0]))

    def attempt_join(self, credentials):
        try:
            self.join(credentials)
        except KeyError as e:
            raise Exception("missing the credential '{0}'".format(e.args[0]))

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
        raise AgentError(
            CONFIGURATION_ERROR,
            message=f"Agent expecting Security Type(s) "
            f"{[Configuration.SECURITY_TYPE_CHOICES[i][1] for i in allowed_config_auth_types]} but got "
            f"Security Type '{Configuration.SECURITY_TYPE_CHOICES[actual_config_auth_type][1]}' instead",
        )


def create_error_response(error_code, error_description):
    response_json = json.dumps({"error_codes": [{"code": error_code, "description": error_description}]})

    return response_json


class MockedMiner(BaseAgent):
    add_error_credentials: dict[str, dict[str, str]] = {}
    existing_card_numbers: dict[str, str] = {}
    ghost_card_prefix: Optional[str] = None
    join_fields: set[str] = set()
    join_prefix = "1"
    retry_limit = None
    titles: list[str] = []

    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.account_status = user_info["status"]
        self.errors = {}
        self.headers = {}
        self.identifier = {}
        self.journey_type = user_info.get("journey_type")
        self.retry_count = retry_count
        self.scheme_id = user_info["scheme_account_id"]
        self.scheme_slug = scheme_slug
        self.user_info = user_info

    def check_and_raise_error_credentials(self, credentials):
        for credential_type, credential in credentials.items():
            try:
                error_to_raise = self.add_error_credentials[credential_type][credential]
                raise LoginError(error_to_raise)
            except KeyError:
                pass

        card_number = credentials.get("card_number") or credentials.get("barcode")
        if self.ghost_card_prefix and card_number and card_number.startswith(self.ghost_card_prefix):
            raise LoginError(PRE_REGISTERED_CARD)

    @staticmethod
    def _check_email_already_exists(email):
        return any(info["credentials"].get("email") == email for info in USER_STORE.values())

    def _check_existing_join_credentials(self, email, ghost_card):
        if ghost_card:
            if ghost_card in self.existing_card_numbers:
                raise JoinError(ACCOUNT_ALREADY_EXISTS)
            if self._check_email_already_exists(email):
                raise JoinError(JOIN_ERROR)
        else:
            if self._check_email_already_exists(email):
                raise JoinError(ACCOUNT_ALREADY_EXISTS)

    def _validate_join_credentials(self, data):
        for join_field in self.join_fields:
            if join_field not in data.keys():
                raise KeyError(join_field)

        email = data.get("email").lower()
        ghost_card = data.get("card_number") or data.get("barcode")
        self._check_existing_join_credentials(email, ghost_card)

        if email == "fail@unknown.com":
            raise JoinError(UNKNOWN)
        elif email == "slowjoin@testbink.com":
            time.sleep(30)

        title = data.get("title").capitalize()
        if self.titles and title not in self.titles:
            raise JoinError(JOIN_ERROR)

        return {"message": "success"}
