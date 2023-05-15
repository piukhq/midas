import json
import logging
import unittest
from unittest.mock import ANY, Mock, patch
from uuid import uuid4

import arrow
import httpretty
import requests

import settings
from app.audit import (  # noqa
    AuditLogger,
    AuditLogType,
    RequestAuditLog,
    ResponseAuditLog,
    sanitise_json,
    sanitise_rpc,
    serialize,
)
from settings import AUDIT_DEFAULT_SENSITIVE_KEYS

standin = settings.SANITISATION_STANDIN


def raise_exception(request, uri, headers):
    raise requests.exceptions.RequestException()


class TestAudit(unittest.TestCase):
    def test_sanitise_sensitive_fields(self):
        payload = {
            "safe data": "this is fine",
            "password": "oh no",
            "some nested data": {
                "secret": "don't tell anyone",
            },
            "token": {"nested structure": "should be removed"},
            "list of items": [
                {
                    "something safe": "don't remove me",
                    "pwd": "👀",
                },
                {
                    "pw": "1234567890",
                    "another safe one": "i'll still be around",
                },
            ],
        }
        expected = {
            "safe data": "this is fine",
            "password": standin,
            "some nested data": {
                "secret": standin,
            },
            "token": standin,
            "list of items": [
                {
                    "something safe": "don't remove me",
                    "pwd": standin,
                },
                {
                    "pw": standin,
                    "another safe one": "i'll still be around",
                },
            ],
        }

        result = sanitise_json(payload, AUDIT_DEFAULT_SENSITIVE_KEYS)
        assert result == expected, "new payload should be sanitised"
        assert payload != result, "original payload should not be changed"

    @httpretty.activate
    def test_sending_to_atlas_excludes_sensitive_fields(self):
        httpretty.register_uri("POST", settings.ATLAS_URL + "/audit/membership/")

        req_message_uid = uuid4().hex
        resp_message_uid = uuid4().hex
        record_uid = uuid4().hex

        logger = AuditLogger()
        logger.send_request_audit_log(
            sender="test",
            payload={"type": "user", "details": {"username": "testuser", "password": "testpass"}, "url": "http://test"},
            scheme_slug="test-scheme",
            handler_type=0,
            integration_service=0,
            message_uid=req_message_uid,
            record_uid=record_uid,
            channel="unit tests",
            audit_config={},
        )
        timestamp = arrow.utcnow().int_timestamp

        expected = {
            "audit_logs": [
                {
                    "audit_log_type": "REQUEST",
                    "channel": "unit tests",
                    "handler_type": "UPDATE",
                    "integration_service": 0,
                    "membership_plan_slug": "test-scheme",
                    "message_uid": req_message_uid,
                    "payload": {
                        "type": "user",
                        "details": {"username": "testuser", "password": standin},
                        "url": "http://test",
                    },
                    "record_uid": record_uid,
                    "timestamp": timestamp,
                },
            ]
        }
        data = json.loads(httpretty.last_request().body.decode("utf-8"))
        assert expected == data

        logger.send_response_audit_log(
            sender="test",
            response="200 ok",
            scheme_slug="test-scheme",
            handler_type=0,
            integration_service=0,
            status_code=200,
            message_uid=resp_message_uid,
            record_uid=record_uid,
            channel="unit tests",
            audit_config={},
        )

        expected = {
            "audit_logs": [
                {
                    "audit_log_type": "RESPONSE",
                    "channel": "unit tests",
                    "handler_type": "UPDATE",
                    "integration_service": 0,
                    "membership_plan_slug": "test-scheme",
                    "message_uid": resp_message_uid,
                    "payload": "200 ok",
                    "record_uid": record_uid,
                    "status_code": 200,
                    "timestamp": ANY,
                },
            ]
        }

        data = json.loads(httpretty.last_request().body.decode("utf-8"))
        assert expected == data

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    def test_atlas_attribute_exception_send_logs(self, mock_send_to_atlas):
        httpretty.register_uri("POST", settings.ATLAS_URL + "/audit/membership/")

        resp_message_uid = uuid4().hex
        record_uid = uuid4().hex

        logger = AuditLogger()

        mock_resp = Mock()
        mock_resp.json.side_effect = AttributeError()
        mock_resp.content = "Not json"
        mock_resp.status_code = 200

        logger.send_response_audit_log(
            sender="test",
            response=mock_resp,
            scheme_slug="test-scheme",
            handler_type=0,
            integration_service=0,
            status_code=200,
            message_uid=resp_message_uid,
            record_uid=record_uid,
            channel="unit tests",
            audit_config={},
        )

        assert mock_send_to_atlas.called
        # Since we forced an AttributeError in mock_response, this should be sent to atlas.
        assert mock_send_to_atlas.call_args[0][0].payload.content == "Not json"

    @httpretty.activate
    @patch("app.audit.AuditLogger.send_to_atlas")
    def test_atlas_json_decode_error_send_logs(self, mock_send_to_atlas):
        httpretty.register_uri("POST", settings.ATLAS_URL + "/audit/membership/")

        resp_message_uid = uuid4().hex
        record_uid = uuid4().hex

        logger = AuditLogger()

        # Create a response that does  not contain json
        httpretty.register_uri(httpretty.GET, "http://example.com/", body="Not json", content_type="application/json")
        response = requests.get("http://example.com/")

        logger.send_response_audit_log(
            sender="test",
            response=response,
            scheme_slug="test-scheme",
            handler_type=0,
            integration_service=0,
            status_code=200,
            message_uid=resp_message_uid,
            record_uid=record_uid,
            channel="unit tests",
            audit_config={},
        )

        assert mock_send_to_atlas.called
        # Since we forced an json decode error in mock_response, this should send the response text.
        assert mock_send_to_atlas.call_args[0][0].payload == "Not json"

    def test_send_to_atlas_no_audit_log(self):
        audit_logger = AuditLogger()
        log_logger = logging.getLogger("audit")
        with self.assertLogs(logger=log_logger, level="DEBUG") as captured:
            result = audit_logger.send_to_atlas(None, {})

        assert captured.records[0].getMessage() == "No request or response data to send to Atlas."

        assert result is None

    @httpretty.activate
    def test_send_to_atlas_resp_not_ok(self):

        httpretty.register_uri("POST", settings.ATLAS_URL + "/audit/membership/", status=404)

        audit_logger = AuditLogger()
        log_logger = logging.getLogger("audit")

        response_audit_log = ResponseAuditLog(
            audit_log_type=AuditLogType.RESPONSE,
            channel="bink",
            membership_plan_slug="scheme_slug",
            handler_type="join",
            message_uid="message_uid_01",
            record_uid="record_uid_01",
            timestamp=arrow.utcnow().int_timestamp,
            integration_service="integration_service",
            payload={"value": "something"},
            status_code=201,
        )

        with self.assertLogs(logger=log_logger, level="DEBUG") as captured:
            audit_logger.send_to_atlas(response_audit_log, {})

        assert "Error response from Atlas when sending audit logs" in captured.records[1].getMessage()

    @httpretty.activate
    def test_send_to_atlas_request_exception(self):
        httpretty.register_uri("POST", settings.ATLAS_URL + "/audit/membership/", body=raise_exception)

        audit_logger = AuditLogger()
        log_logger = logging.getLogger("audit")

        response_audit_log = ResponseAuditLog(
            audit_log_type=AuditLogType.RESPONSE,
            channel="bink",
            membership_plan_slug="scheme_slug",
            handler_type="join",
            message_uid="message_uid_01",
            record_uid="record_uid_01",
            timestamp=arrow.utcnow().int_timestamp,
            integration_service="integration_service",
            payload={"value": "something"},
            status_code=201,
        )

        with self.assertLogs(logger=log_logger) as captured:
            audit_logger.send_to_atlas(response_audit_log, {})

        assert "Error sending audit logs to Atlas" in captured.records[1].getMessage()

    @patch("app.audit.sanitise_rpc")
    @patch("app.audit.sanitise_json")
    def test_correct_sanitise_method_called_when_rpc(self, mock_sanitise_json, mock_sanitise_rpc):
        audit_log = RequestAuditLog(
            audit_log_type=AuditLogType.REQUEST,
            channel="",
            membership_plan_slug="slug",
            handler_type=0,
            record_uid="123",
            timestamp="",
            message_uid="",
            integration_service="",
            payload={
                "original_payload": {
                    "jsonrpc": "2.0",
                    "params": [
                        "this is fine",
                        "this is fine",
                        "oh no",
                        "this is fine",
                        "oh no!",
                        "this is fine",
                        "this is fine",
                    ],
                },
                "audit_translated_payload": {"key": "val", "key": "val"},
            },
        )
        audit_config = {"type": "jsonrpc", "audit_sensitive_keys": [2, 4]}
        serialize(audit_log, audit_config)
        assert mock_sanitise_rpc.called
        assert mock_sanitise_json.called is False

    def test_sanitise_sensitive_audit_fields(self):
        payload = {
            "audit_log_type": "REQUEST",
            "payload": {
                "original_payload": {
                    "jsonrpc": "2.0",
                    "params": [
                        "this is fine",
                        "this is fine",
                        "oh no",
                        "this is fine",
                        "oh no!",
                        "this is fine",
                        "this is fine",
                    ],
                },
                "audit_translated_payload": {"key": "val", "key": "val"},
            },
        }
        expected = {
            "audit_log_type": "REQUEST",
            "payload": {
                "original_payload": {
                    "jsonrpc": "2.0",
                    "params": [
                        "this is fine",
                        "this is fine",
                        standin,
                        "this is fine",
                        standin,
                        "this is fine",
                        "this is fine",
                    ],
                },
                "audit_translated_payload": {"key": "val", "key": "val"},
            },
        }
        result = sanitise_rpc(payload, [2, 4])
        assert result == expected
