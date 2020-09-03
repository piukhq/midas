import json
from enum import Enum
from typing import Union, Iterable, NamedTuple, List, Tuple
from uuid import uuid4

import arrow
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests import Response

from app.utils import get_headers
from settings import logger, ATLAS_URL


class AuditLogType(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"


class RequestAuditLog(NamedTuple):
    audit_log_type: AuditLogType
    channel: str
    membership_plan_slug: str
    handler_type: str
    message_uid: str
    record_uid: str
    timestamp: int
    integration_service: str
    payload: dict

    def serialize(self):
        audit_log = self._asdict()
        audit_log["audit_log_type"] = audit_log["audit_log_type"].value
        return audit_log


class ResponseAuditLog(NamedTuple):
    audit_log_type: AuditLogType
    channel: str
    membership_plan_slug: str
    handler_type: str
    message_uid: str
    record_uid: str
    timestamp: int
    integration_service: str
    payload: Union[dict, str]
    status_code: int

    def serialize(self):
        audit_log = self._asdict()
        audit_log["audit_log_type"] = audit_log["audit_log_type"].value
        return audit_log


class AuditLogger:
    """
    Handler for sending request/response audit logs to Atlas.
    Can be initialised with 2 option arguments:
         channel: A string identifying the channel from which the request was made or the request is related
         journeys: An iterable (Tuple recommended) of journey types for which auditing should be enabled.
            These should be handler_type values defined in the Configuration class e.g Configuration.JOIN_HANDLER
    """

    def __init__(self, channel: str = "", journeys: Iterable[str] = "__all__") -> None:
        self.audit_logs = []
        self.channel = channel
        self.session = requests.Session()
        self.journeys = journeys

    def add_request(
        self,
        payload: Union[Iterable[dict], dict],
        scheme_slug: str,
        handler_type: Tuple[int, str],
        integration_service: str,
        message_uid: str,
        record_uid: str,
    ) -> None:
        self._add_audit_log(
            payload, scheme_slug, handler_type, integration_service, message_uid, record_uid,
            log_type=AuditLogType.REQUEST
        )

    def add_response(
        self,
        response: Union[str, Response],
        scheme_slug: str,
        handler_type: Tuple[int, str],
        integration_service: str,
        status_code: int,
        message_uid: str,
        record_uid: str,
    ) -> None:
        if isinstance(response, str):
            data = response
        else:
            try:
                data = response.json()
            except (json.decoder.JSONDecodeError, TypeError):
                data = response.text

        self._add_audit_log(
            data, scheme_slug, handler_type, integration_service, message_uid, record_uid,
            log_type=AuditLogType.RESPONSE,
            status_code=status_code,
        )

    def retry_session(self, backoff_factor: float = 0.3) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=backoff_factor,
            method_whitelist=False,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # @celery.task
    def send_to_atlas(self):
        if not self.audit_logs:
            logger.debug("No request or response data to send to Atlas")
            return

        headers = get_headers(tid=str(uuid4()))

        try:
            self.audit_logs = self.filter_fields(self.audit_logs)
        except Exception:
            logger.exception(f"Error when filtering fields for atlas audit")

        payload = {'audit_logs': [audit_log.serialize() for audit_log in self.audit_logs if audit_log is not None]}
        logger.info(payload)

        try:
            resp = self.session.post(f"{ATLAS_URL}/audit/membership/", headers=headers, json=payload)
            if resp.ok:
                logger.info("Successfully sent audit logs to Atlas")
                self.audit_logs.clear()
            else:
                logger.error(f"Error response from Atlas when sending audit logs - response: {resp.content}")
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error sending audit logs to Atlas. Error: {repr(e)}")

    @staticmethod
    def filter_fields(req_audit_logs: List[RequestAuditLog]) -> List[RequestAuditLog]:
        """
        Override per merchant to modify which fields are omitted/encrypted.

        This should iterate over req_audit_logs and filter them all in one go as this
        function is only called once before sending to atlas.

        Audit objects may contain references to objects that are used elsewhere and so should
        not be modified directly. Use a copy or deepcopy if modifying values e.g encrypting fields
        in the payload.
        """
        return req_audit_logs

    def _add_audit_log(
        self,
        data: dict,
        scheme_slug: str,
        handler_type: Tuple[int, str],
        integration_service: str,
        message_uid: str,
        record_uid: str,
        log_type: AuditLogType,
        status_code: int = None,
    ) -> None:

        handler_type_int, handler_type_str = handler_type

        def _build_audit_log(log_data: Union[dict, str]) -> Union[RequestAuditLog, ResponseAuditLog]:
            timestamp = arrow.utcnow().timestamp

            if log_type == AuditLogType.REQUEST:
                audit_log = self._build_request_audit_log(
                    log_data, scheme_slug, handler_type_str, integration_service, timestamp, message_uid,
                    record_uid
                )
            elif log_type == AuditLogType.RESPONSE:
                audit_log = self._build_response_audit_log(
                    log_data, scheme_slug, handler_type_str, status_code, integration_service, timestamp,
                    message_uid, record_uid
                )
            else:
                raise ValueError("Invalid AuditLogType provided")
            return audit_log

        if self.journeys == "__all__" or handler_type_int in self.journeys:
            if isinstance(data, list):
                for req in data:
                    self.audit_logs.append(_build_audit_log(req))

            elif isinstance(data, (dict, str)):
                self.audit_logs.append(_build_audit_log(data))

            else:
                logger.warning("Audit log data must be a dict/string or a list of dicts/strings")
        else:
            logger.debug(
                f"Audit logging is disabled for journey type {handler_type_str} for scheme {scheme_slug}"
            )

    def _build_request_audit_log(
        self,
        data: dict,
        scheme_slug: str,
        handler_type: str,
        integration_service: str,
        timestamp: int,
        message_uid: str,
        record_uid: str,
    ) -> RequestAuditLog:
        try:
            return RequestAuditLog(
                audit_log_type=AuditLogType.REQUEST,
                channel=self.channel,
                membership_plan_slug=scheme_slug,
                handler_type=handler_type,
                message_uid=message_uid,
                record_uid=record_uid,
                timestamp=timestamp,
                integration_service=integration_service,
                payload=data
            )
        except KeyError as e:
            logger.warning(
                f"Missing key field for request audit log {e} "
                f"- data provided: {data}"
            )

    def _build_response_audit_log(
        self,
        data: Union[dict, str],
        scheme_slug: str,
        handler_type: str,
        status_code: int,
        integration_service: str,
        timestamp: int,
        message_uid: str,
        record_uid: str,
    ) -> ResponseAuditLog:
        try:
            return ResponseAuditLog(
                audit_log_type=AuditLogType.RESPONSE,
                channel=self.channel,
                membership_plan_slug=scheme_slug,
                handler_type=handler_type,
                message_uid=message_uid,
                record_uid=record_uid,
                timestamp=timestamp,
                integration_service=integration_service,
                payload=data,
                status_code=status_code
            )
        except KeyError as e:
            logger.warning(
                f"Missing key field for response audit log {e} "
                f"- data provided: {data}"
            )
