import json
from enum import Enum
from typing import Union, Iterable, NamedTuple
from uuid import uuid4

import arrow
import requests
from requests import Response

from app.utils import get_headers
from settings import logger, ATLAS_URL


class AuditLogType(Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"


class RequestAuditLog(NamedTuple):
    audit_log_type: AuditLogType
    channel: str
    membership_plan_slug: str
    handler_type: str
    bink_message_uid: str
    bink_record_uid: str
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
    bink_message_uid: str
    bink_record_uid: str
    timestamp: int
    integration_service: str
    payload: Union[dict, str]
    status_code: int

    def serialize(self):
        audit_log = self._asdict()
        audit_log["audit_log_type"] = audit_log["audit_log_type"].value
        return audit_log


class AuditLogger:

    def __init__(
        self,
        channel: str = ""
    ) -> None:
        self.audit_logs = []
        self.channel = channel

    def add_request(
        self,
        payload: Union[Iterable[dict], dict],
        scheme_slug: str,
        handler_type: str,
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
        response: Response,
        scheme_slug: str,
        handler_type: str,
        integration_service: str,
        status_code: int,
        message_uid: str,
        record_uid: str,
        response_body: str,
    ) -> None:

        try:
            data = response.json()
        except json.decoder.JSONDecodeError:
            data = response.text

        self._add_audit_log(
            data, scheme_slug, handler_type, integration_service, message_uid, record_uid,
            log_type=AuditLogType.RESPONSE,
            status_code=status_code,
        )

    # @celery.task
    def send_to_atlas(self):
        if not self.audit_logs:
            logger.debug("No request or response data to send to Atlas")
            return

        headers = get_headers(tid=str(uuid4()))

        self.filter_fields()
        payload = {'audit_logs': [audit_log.serialize() for audit_log in self.audit_logs if audit_log is not None]}

        logger.info(payload)

        try:
            resp = requests.post(f"{ATLAS_URL}/audit/enrol/enrol-audit", headers=headers, json=payload)
            if resp.ok:
                logger.info("Successfully sent audit logs to Atlas")
                self.audit_logs.clear()
            else:
                logger.error(f"Error response from Atlas when sending audit logs - response: {resp.content}")
        except requests.exceptions.RequestException:
            logger.exception("Error sending audit logs to Atlas")

    def filter_fields(self) -> Iterable[RequestAuditLog]:
        """Override per merchant to modify which fields are omitted/encrypted"""
        pass

    def _add_audit_log(
        self,
        data: dict,
        scheme_slug: str,
        handler_type: str,
        integration_service: str,
        message_uid: str,
        record_uid: str,
        log_type: AuditLogType,
        status_code: int = None,
    ) -> None:

        def _build_audit_log(log_data: Union[dict, str]) -> Union[RequestAuditLog, ResponseAuditLog]:
            timestamp = arrow.utcnow().timestamp

            if log_type == AuditLogType.REQUEST:
                audit_log = self._build_request_audit_log(
                    log_data, scheme_slug, handler_type, integration_service, timestamp, message_uid,
                    record_uid
                )
            elif log_type == AuditLogType.RESPONSE:
                audit_log = self._build_response_audit_log(
                    log_data, scheme_slug, handler_type, status_code, integration_service, timestamp,
                    message_uid, record_uid
                )
            else:
                raise ValueError("Invalid AuditLogType provided")
            return audit_log

        if isinstance(data, list):
            for req in data:
                self.audit_logs.append(_build_audit_log(req))

        elif isinstance(data, (dict, str)):
            self.audit_logs.append(_build_audit_log(data))

        else:
            logger.warning("Audit log data must be a dict/string or a list of dicts/strings")

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
                bink_message_uid=message_uid,
                bink_record_uid=record_uid,
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
                bink_message_uid=message_uid,
                bink_record_uid=record_uid,
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
