import json
from enum import Enum
from typing import Any, Iterable, NamedTuple, Union
from uuid import uuid4

import arrow
import requests
from blinker import signal
from requests import Response
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from soteria.configuration import Configuration

from app.http_request import get_headers
from app.reporting import get_logger
from settings import ATLAS_URL


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
    payload: Union[dict, str]


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


AuditLog = Union[RequestAuditLog, ResponseAuditLog]


def serialize(audit_log: AuditLog) -> dict:
    data = audit_log._asdict()
    data["audit_log_type"] = data["audit_log_type"].value
    return data


log = get_logger("audit")


class AuditLogger:
    """
    Handler for sending request/response audit logs to Atlas.
    Can be initialised with 2 optional arguments:
         channel: A string identifying the channel from which the request was made or the request is related
         journeys: An iterable (Tuple recommended) of journey types for which auditing should be enabled.
            These should be handler_type values defined in the Configuration class e.g Configuration.JOIN_HANDLER
    """

    def __init__(self, journeys: Iterable[Union[str, int]] = "__all__") -> None:
        self.session = self.retry_session()
        self.journeys = journeys

        signal("send-audit-request").connect(self.send_request_audit_log)
        signal("send-audit-response").connect(self.send_response_audit_log)

    def send_request_audit_log(
        self,
        sender: Union[object, str],
        payload: Union[dict[Any, Any], str],
        scheme_slug: str,
        handler_type: int,
        integration_service: str,
        message_uid: str,
        record_uid: str,
        channel: str,
    ) -> None:
        timestamp = arrow.utcnow().int_timestamp
        handler_type_str = Configuration.handler_type_as_str(handler_type)
        request_audit_log = RequestAuditLog(
            audit_log_type=AuditLogType.REQUEST,
            channel=channel,
            membership_plan_slug=scheme_slug,
            handler_type=handler_type_str,
            message_uid=message_uid,
            record_uid=record_uid,
            timestamp=timestamp,
            integration_service=integration_service,
            payload=payload,
        )
        self.send_to_atlas(request_audit_log)

    def send_response_audit_log(
        self,
        sender: Union[object, str],
        response: Response,
        scheme_slug: str,
        handler_type: int,
        integration_service: str,
        status_code: int,
        message_uid: str,
        record_uid: str,
        channel: str,
    ):
        timestamp = arrow.utcnow().int_timestamp
        handler_type_str = Configuration.handler_type_as_str(handler_type)
        try:
            data = response.json()
        except AttributeError:
            data = response
        except (json.decoder.JSONDecodeError, TypeError):
            data = response.text

        response_audit_log = ResponseAuditLog(
            audit_log_type=AuditLogType.RESPONSE,
            channel=channel,
            membership_plan_slug=scheme_slug,
            handler_type=handler_type_str,
            message_uid=message_uid,
            record_uid=record_uid,
            timestamp=timestamp,
            integration_service=integration_service,
            payload=data,
            status_code=status_code,
        )
        self.send_to_atlas(response_audit_log)

    def send_to_atlas(self, audit_log):
        if not audit_log:
            log.debug("No request or response data to send to Atlas.")
            return

        headers = get_headers(tid=str(uuid4()))
        payload = {"audit_logs": [serialize(audit_log)]}
        log.info(f"Sending payload to atlas: {payload}")

        try:
            resp = self.session.post(f"{ATLAS_URL}/audit/membership/", headers=headers, json=payload)
            if resp.ok:
                log.info("Successfully sent audit logs to Atlas.")
            else:
                resp_content = resp.content.decode("utf-8")
                log.error(f"Error response from Atlas when sending audit logs. Response: {resp_content}")
        except requests.exceptions.RequestException as e:
            log.exception(f"Error sending audit logs to Atlas. Error: {repr(e)}")

    def retry_session(self, backoff_factor: float = 0.3) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3, backoff_factor=backoff_factor, method_whitelist=False, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
