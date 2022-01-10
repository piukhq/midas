import hashlib
import json
import time
from collections import defaultdict
from decimal import Decimal
from typing import Optional
from urllib.parse import urlsplit, urlparse
from uuid import uuid4

import arrow
import requests
from blinker import signal
from redis import RedisError
from requests import HTTPError
from requests.exceptions import Timeout
from soteria.configuration import Configuration
from tenacity import retry, retry_if_exception_type, stop_after_attempt

import settings
from app import publish
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    CARD_NOT_REGISTERED,
    CARD_NUMBER_ERROR,
    END_SITE_DOWN,
    GENERAL_ERROR,
    IP_BLOCKED,
    JOIN_ERROR,
    JOIN_IN_PROGRESS,
    LINK_LIMIT_EXCEEDED,
    NO_SUCH_RECORD,
    NOT_SENT,
    PRE_REGISTERED_CARD,
    RETRY_LIMIT_REACHED,
    STATUS_LOGIN_FAILED,
    UNKNOWN,
    VALIDATION,
    AgentError,
    JoinError,
    LoginError,
    RetryLimitError,
    UnauthorisedError,
    errors,
)
from app.agents.schemas import Balance, Transaction
from app.audit import AuditLogger
from app.back_off_service import BackOffService
from app.constants import ENCRYPTED_CREDENTIALS
from app.encryption import hash_ids
from app.exceptions import AgentException
from app.mocks.users import USER_STORE
from app.publish import thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus, update_pending_join_account
from app.security.utils import get_security_agent
from app.tasks.resend_consents import ConsentStatus, send_consent_status

log = get_logger("agent-base")


class BaseMiner(object):
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
    scheme_id = -1  # this is replaced by the derived classes. remove this when bases are merged into one.

    def join(self, credentials):
        raise NotImplementedError()

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self) -> Optional[Balance]:
        raise NotImplementedError()

    def scrape_transactions(self) -> list[dict]:
        raise NotImplementedError()

    def parse_transaction(self, transaction: dict) -> Optional[Transaction]:
        raise NotImplementedError()

    def calculate_label(self, points: Decimal) -> str:
        raise NotImplementedError()

    def transactions(self) -> list[Transaction]:
        try:
            return self.hash_transactions(
                [parsed_tx for raw_tx in self.scrape_transactions() if (parsed_tx := self.parse_transaction(raw_tx))]
            )
        except Exception as ex:
            log.warning(f"{self} failed to get transactions: {repr(ex)}")
            return []

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


# Based on requests library
class ApiMiner(BaseMiner):
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
        self.audit_logger = AuditLogger(channel=self.channel)
        self.audit_finished = False
        self.audit_handlers = {
            JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
            JourneyTypes.ADD: Configuration.VALIDATE_HANDLER,
            JourneyTypes.UPDATE: Configuration.UPDATE_HANDLER,
        }

    def send_audit_logs(self, payload, resp):
        if payload.get("password"):
            payload["password"] = "REDACTED"

        record_uid = hash_ids.encode(self.scheme_id)
        handler_type = self.audit_handlers[self.journey_type]
        message_uid = str(uuid4())
        signal("add-audit-request").send(
            self,
            payload=payload,
            scheme_slug=self.scheme_slug,
            handler_type=handler_type,
            integration_service=self.integration_service,
            message_uid=message_uid,
            record_uid=record_uid,
        )
        signal("add-audit-response").send(
            self,
            response=resp,
            scheme_slug=self.scheme_slug,
            handler_type=handler_type,
            integration_service=self.integration_service,
            status_code=resp.status_code,
            message_uid=message_uid,
            record_uid=record_uid,
        )
        signal("send-to-atlas").send(self)

    def make_request(self, url, method="get", timeout=5, **kwargs):
        # Combine the passed kwargs with our headers and timeout values.
        send_audit = False
        if "json" in kwargs or "data" in kwargs:
            audit_payload = kwargs["json"] if kwargs.get("json") else kwargs["data"]
        else:
            audit_payload = urlparse(url).query

        if self.journey_type in self.audit_handlers.keys() and not self.audit_finished:
            send_audit = True

        path = urlsplit(url).path  # Get the path part of the url for signal call

        args = {
            "headers": self.headers,
            "timeout": timeout,
        }
        args.update(kwargs)

        try:
            resp = requests.request(method, url=url, **args)
            signal("record-http-request").send(
                self,
                slug=self.scheme_slug,
                endpoint=path,
                latency=resp.elapsed.total_seconds(),
                response_code=resp.status_code,
            )
            if send_audit:
                self.send_audit_logs(audit_payload, resp)

        except Timeout as exception:
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error="Timeout")
            raise AgentError(END_SITE_DOWN) from exception

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
            signal("request-fail").send(self, slug=self.scheme_slug, channel=self.channel, error=END_SITE_DOWN)
            raise AgentError(END_SITE_DOWN, response=e.response) from e

        return resp

    def handle_errors(self, response, exception_type=LoginError, unhandled_exception_code=UNKNOWN):
        for key, values in self.errors.items():
            if response in values:
                raise exception_type(key)
        raise AgentError(unhandled_exception_code)


def create_error_response(error_code, error_description):
    response_json = json.dumps({"error_codes": [{"code": error_code, "description": error_description}]})

    return response_json


class MerchantApi(BaseMiner):
    """
    Base class for merchant API integrations.
    """

    retry_limit = 9  # tries 10 times overall
    credential_mapping = {
        "date_of_birth": "dob",
        "phone": "phone1",
        "phone_2": "phone2",
    }
    identifier_type = ["barcode", "card_number", "merchant_scheme_id2"]
    # used to map merchant identifiers to scheme credential types
    merchant_identifier_mapping = {
        "merchant_scheme_id2": "merchant_identifier",
    }

    ERRORS_KEYS = ["error_codes", "errors"]

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None, consents_data=None):
        self.retry_count = retry_count
        self.scheme_id = user_info["scheme_account_id"]
        self.scheme_slug = scheme_slug
        self.user_info = user_info
        self.config = config
        self.consents_data = consents_data

        self.message_uid = None
        self.record_uid = None
        self.request = None
        self.result = None
        channel = user_info.get("channel", "")
        self.audit_logger = AuditLogger(channel=channel)

        # { error we raise: error we receive in merchant payload }
        self.errors = {
            NOT_SENT: ["NOT_SENT"],
            NO_SUCH_RECORD: ["NO_SUCH_RECORD"],
            STATUS_LOGIN_FAILED: ["VALIDATION"],
            ACCOUNT_ALREADY_EXISTS: ["ALREADY_PROCESSED", "ACCOUNT_ALREADY_EXISTS"],
            PRE_REGISTERED_CARD: ["PRE_REGISTERED_ERROR"],
            UNKNOWN: ["UNKNOWN"],
            # additional mappings for iceland
            CARD_NOT_REGISTERED: ["CARD_NOT_REGISTERED"],
            GENERAL_ERROR: ["GENERAL_ERROR"],
            CARD_NUMBER_ERROR: ["CARD_NUMBER_ERROR"],
            LINK_LIMIT_EXCEEDED: ["LINK_LIMIT_EXCEEDED"],
            JOIN_IN_PROGRESS: ["JOIN_IN_PROGRESS"],
            JOIN_ERROR: ["JOIN_ERROR"],
        }

    def login(self, credentials):
        """
        Calls handler, passing in handler_type as either 'validate' or 'update' depending on if a link
        request was made or not. A link boolean should be in the credentials to check if request was a link.
        :param credentials: user account credentials for merchant scheme
        :return: None
        """
        account_link = self.user_info["journey_type"] == JourneyTypes.LINK.value

        self.record_uid = hash_ids.encode(self.scheme_id)
        handler_type = Configuration.VALIDATE_HANDLER if account_link else Configuration.UPDATE_HANDLER

        # Will be an empty dict if retries exhausted, or a dict that can be checked for an error
        self.result = self._outbound_handler(credentials, self.scheme_slug, handler_type=handler_type)

        error = self._check_for_error_response(self.result)
        if error:
            signal("log-in-fail").send(self, slug=self.scheme_slug)
            signal("request-fail").send(
                self,
                slug=self.scheme_slug,
                channel=self.user_info.get("channel", ""),
                error=error[0]["code"],
            )
            self._handle_errors(error[0]["code"], exception_type=LoginError)
        else:  # Login will have succeeded, unless an empty dict was returned by _outbound_handler()
            if self.result:
                signal("log-in-success").send(self, slug=self.scheme_slug)
            else:
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                signal("request-fail").send(
                    self,
                    slug=self.scheme_slug,
                    channel=self.user_info.get("channel", ""),
                    error="Retry limit reached",
                )

        # For adding the scheme account credential answer to db after first successful login or if they change.
        identifiers = self._get_identifiers(self.result)
        self.identifier = {}
        try:
            for key, value in identifiers.items():
                if credentials[key] != value:
                    self.identifier[key] = value
        except KeyError:
            self.identifier = identifiers

    def join(self, data, inbound=False):
        """
        Calls handler, passing in 'join' as the handler_type.
        :param data: user account credentials to join for merchant scheme or validated merchant response data
        for outbound or inbound processes respectively.
        :param inbound: Boolean for if the data should be handled for an inbound response or outbound request
        :return: None
        """
        consents_data = self.user_info["credentials"].get("consents")
        self.consents_data = consents_data.copy() if consents_data else []
        log.debug(f"Joining with consents: {consents_data} and scheme slug: {self.scheme_slug}")

        if inbound:
            self._async_inbound(data, self.scheme_slug, handler_type=Configuration.JOIN_HANDLER)
        else:
            "TODO: REMOVE THE FOLLOWING ASAP, when we have a ticket!"
            "TEMPORARY FOR ICELAND CONSENTS"
            if self.scheme_slug == "iceland-bonus-card" and self.consents_data:
                if len(self.consents_data) < 2:
                    journey_type = self.consents_data[0]["journey_type"]
                    consent = {
                        "id": 99999999999,
                        "slug": "marketing_opt_in_thirdparty",
                        "value": False,
                        "created_on": arrow.now().isoformat(),  # '2020-05-26T15:30:16.096802+00:00',
                        "journey_type": journey_type,
                    }
                    data["consents"].append(consent)
                else:
                    log.debug("Too many consents for Iceland scheme.")

            self.record_uid = data["record_uid"] = hash_ids.encode(self.scheme_id)

            self.result = self._outbound_handler(data, self.scheme_slug, handler_type=Configuration.JOIN_HANDLER)

            # Async joins will return empty 200 responses so there is nothing to process.
            if self.config.integration_service == "SYNC":
                self.process_join_response()

            # Processing immediate response from async requests
            else:
                consent_status = ConsentStatus.PENDING
                try:
                    error = self._check_for_error_response(self.result)
                    if error:
                        self._handle_errors(error[0]["code"], exception_type=JoinError)

                except (AgentException, LoginError, AgentError):
                    consent_status = ConsentStatus.FAILED
                    raise
                finally:
                    self.consent_confirmation(self.consents_data, consent_status)

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
                self._handle_errors(error[0]["code"], exception_type=JoinError)

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

    def _outbound_handler(self, data, scheme_slug, handler_type) -> dict:
        """
        Handler service to apply merchant configuration and build JSON, for request to the merchant, and
        handles response. Configuration service is called to retrieve merchant config.
        :param data: python object data to be built into the JSON object.
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :param handler_type: Int. A choice from Configuration.HANDLER_TYPE_CHOICES
        :return: dict of response data
        """
        self.message_uid = str(uuid4())
        if not self.config:
            self.config = Configuration(
                scheme_slug,
                handler_type,
                settings.VAULT_URL,
                settings.VAULT_TOKEN,
                settings.CONFIG_SERVICE_URL,
            )

        if handler_type == Configuration.JOIN_HANDLER:
            data["country"] = self.config.country
            async_service_identifier = Configuration.INTEGRATION_CHOICES[Configuration.ASYNC_INTEGRATION][1].upper()
            if self.config.integration_service == async_service_identifier:
                self.expecting_callback = True

        data["message_uid"] = self.message_uid
        data["record_uid"] = self.record_uid
        data["callback_url"] = self.config.callback_url

        self._filter_consents(data, handler_type)

        merchant_scheme_ids = self.get_merchant_ids(data)
        data.update(merchant_scheme_ids)

        data = self.map_credentials_to_request(data)
        payload = json.dumps(data)

        # data without encrypted credentials for logging only
        temp_data = {k: v for k, v in data.items() if k not in ENCRYPTED_CREDENTIALS}

        logging_info = self._create_log_message(
            temp_data,
            self.message_uid,
            scheme_slug,
            self.config.handler_type,
            self.config.integration_service,
            "OUTBOUND",
        )

        log.info(json.dumps(logging_info))

        response_json: Optional[str] = self._sync_outbound(payload)

        response_data = {}
        if response_json:
            response_data = json.loads(response_json)

            logging_info["direction"] = "INBOUND"
            logging_info["json"] = response_data
            if self._check_for_error_response(response_data):
                logging_info["contains_errors"] = True
                log.warning(json.dumps(logging_info))
            else:
                log.info(json.dumps(logging_info))

        signal("send-to-atlas").send()
        return response_data

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

        signal("add-audit-response").send(
            response=json.dumps(data),
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            scheme_slug=self.scheme_slug,
            handler_type=self.config.handler_type[0],
            integration_service=self.config.integration_service,
            status_code=0,  # Doesn't have a status code since this is an async response
        )
        signal("send-to-atlas").send()

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

    def apply_security_measures(self, json_data, security_service, security_credentials):
        outbound_security_agent = get_security_agent(security_service, security_credentials)
        self.request = outbound_security_agent.encode(json_data)

    def _sync_outbound(self, json_data):
        """
        Synchronous outbound service to build a request and make call to merchant endpoint.
        Calls are made to security and back off services pre-request. Security measures are reapplied before
        retrying if an unauthorised response is returned.
        :param json_data: JSON string of payload to send to merchant
        :return: Response payload
        """

        def apply_security_measures(retry_state):
            return self.apply_security_measures(
                json_data,
                self.config.security_credentials["outbound"]["service"],
                self.config.security_credentials,
            )

        @retry(
            stop=stop_after_attempt(2),
            retry=retry_if_exception_type(UnauthorisedError),
            before=apply_security_measures,
            reraise=True,
        )
        def send_request():
            # This is to refresh auth creds and retry the request on Unauthorised errors.
            # These errors will result in additional retries to the retry_count below.
            return self._send_request()

        back_off_service = BackOffService()

        response_json = None
        for retry_count in range(1 + self.config.retry_limit):
            try:
                service_on_cooldown = back_off_service.is_on_cooldown(self.config.scheme_slug, self.config.scheme_slug)
            except RedisError as ex:
                log.warning(f"Backoff service error. Presuming not on cool down: {ex}")
                service_on_cooldown = False

            if service_on_cooldown:
                error_desc = "{} {} is currently on cooldown".format(errors[NOT_SENT]["name"], self.config.scheme_slug)
                response_json = create_error_response(NOT_SENT, error_desc)
                break
            else:
                try:
                    response_json, status = send_request()

                    if status in [200, 202]:
                        break
                except UnauthorisedError:
                    response_json = create_error_response(VALIDATION, errors[VALIDATION]["name"])
                if retry_count == self.config.retry_limit:
                    try:
                        back_off_service.activate_cooldown(
                            self.config.scheme_slug,
                            self.config.handler_type,
                            settings.BACK_OFF_COOLDOWN,
                        )
                    except RedisError as ex:
                        log.warning(f"Error activating cool down for {self.config.scheme_slug}: {ex}")

        return response_json

    def _send_request(self):
        signal("add-audit-request").send(
            payload=self.request["json"],
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            scheme_slug=self.config.scheme_slug,
            handler_type=self.config.handler_type[0],
            integration_service=self.config.integration_service,
        )

        response = requests.post(f"{self.config.merchant_url}", **self.request)
        status = response.status_code

        signal("record-http-request").send(
            self,
            slug=self.scheme_slug,
            endpoint=response.request.path_url,
            latency=response.elapsed.total_seconds(),
            response_code=status,
        )

        log.debug(f"Raw response: {response.text}, HTTP status: {status}, scheme_account: {self.scheme_id}")

        signal("add-audit-response").send(
            response=response,
            message_uid=self.message_uid,
            record_uid=self.record_uid,
            scheme_slug=self.config.scheme_slug,
            handler_type=self.config.handler_type[0],
            integration_service=self.config.integration_service,
            status_code=status,
        )

        # Send signal for fail if not 2XX response
        if status not in [200, 202]:
            signal("request-fail").send(
                self,
                slug=self.scheme_slug,
                channel=self.user_info.get("channel", ""),
                error=response.reason,
            )

        if status in [200, 202]:
            signal("request-success").send(self, slug=self.scheme_slug, channel=self.user_info.get("channel", ""))
            if self.config.security_credentials["outbound"]["service"] == Configuration.OAUTH_SECURITY:
                inbound_security_agent = get_security_agent(Configuration.OPEN_AUTH_SECURITY)
            else:
                inbound_security_agent = get_security_agent(
                    self.config.security_credentials["inbound"]["service"],
                    self.config.security_credentials,
                )

            response_json = inbound_security_agent.decode(response.headers, response.text)

            self.log_if_redirect(response, response_json)
        elif status == 401:
            raise UnauthorisedError
        elif status in [503, 504, 408]:
            response_json = create_error_response(NOT_SENT, errors[NOT_SENT]["name"])
        else:
            response_json = create_error_response(
                UNKNOWN, errors[UNKNOWN]["name"] + " with status code {}".format(status)
            )

        return response_json, status

    def _async_inbound(self, data, scheme_slug, handler_type):
        """
        Asynchronous inbound service that will set logging level based on configuration per merchant and return
        a success response asynchronously before calling the inbound handler service.
        :param data: dict of validated merchant response data.
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :param handler_type: Int. A choice from Configuration.HANDLER_TYPE_CHOICES
        :return: None
        """
        if not self.config:
            self.config = Configuration(
                scheme_slug,
                handler_type,
                settings.VAULT_URL,
                settings.VAULT_TOKEN,
                settings.CONFIG_SERVICE_URL,
            )

        self.record_uid = hash_ids.encode(self.scheme_id)

        # asynchronously call handler
        thread_pool_executor.submit(self._inbound_handler, data, self.scheme_slug)

    # agents will override this if unique values are needed
    def get_merchant_ids(self, credentials):
        user_id = sorted(map(int, self.user_info["user_set"].split(",")))[0]
        merchant_ids = {
            "merchant_scheme_id1": hash_ids.encode(user_id),
            "merchant_scheme_id2": credentials.get("merchant_identifier"),
        }

        return merchant_ids

    def _handle_errors(self, response, exception_type=AgentError):
        for key, values in self.errors.items():
            if response in values:
                raise exception_type(key)
        raise AgentError(UNKNOWN)

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

    def _get_identifiers(self, data):
        """Checks if data contains any identifiers (i.e barcode, card_number) and returns a dict with their values."""
        _identifier = {}
        for identifier in self.identifier_type:
            value = data.get(identifier)
            if value:
                converted_credential_type = self.merchant_identifier_mapping.get(identifier) or identifier
                _identifier[converted_credential_type] = value
        return _identifier

    def map_credentials_to_request(self, data):
        """
        Converts credential keys to correct JSON keys in merchant request.
        Agents will override the credential_mapping class attribute to define the changes.
        :param data: dict of credentials being sent to merchant.
        :return: dict of credentials with keys converted into the keys to be sent to a merchant.
        """
        for key, value in self.credential_mapping.items():
            if key in data:
                data[value] = data.pop(key)
        return data

    def _check_for_error_response(self, response):
        error = None
        for key in self.ERRORS_KEYS:
            error = response.get(key)
            if error:
                break
        return error

    @staticmethod
    def _filter_consents(data, handler_type):
        """
        Filters consents depending on handler/journey type and adds to request data in the correct format.
        :param data: dict. contains credentials including consents if available.
        {
            'email': '',
            'password: '',
            'consents': [{'id': 1, 'value': True, 'slug': 'consent', 'journey_type': 1, 'created_on': ''}]
            ...
        }
        :param handler_type: Int. A choice from Configuration.HANDLER_TYPE_CHOICES
        :return: None
        """
        # JourneyTypes are used across projects whereas handler types only exist in midas. Since they differ,
        # a mapping is required.
        journey_types = {
            Configuration.JOIN_HANDLER: JourneyTypes.JOIN,
            Configuration.VALIDATE_HANDLER: JourneyTypes.LINK,
        }

        try:
            consents = data.pop("consents")
            journey = journey_types[handler_type]
        except KeyError:
            return

        for consent in consents:
            if consent["journey_type"] == journey:
                data.update({consent["slug"]: consent["value"]})

    def log_if_redirect(self, response, message):
        if response.history:
            logging_info = self._create_log_message(
                message,
                json.loads(self.request["json"])["message_uid"],
                self.config.scheme_slug,
                self.config.handler_type,
                self.config.integration_service,
                "OUTBOUND",
            )
            log.warning(json.dumps(logging_info))


class MockedMiner(BaseMiner):
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
