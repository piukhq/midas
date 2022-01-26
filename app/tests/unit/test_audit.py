import json
import unittest
from unittest.mock import ANY
from uuid import uuid4

import arrow
import httpretty

import settings

settings.ATLAS_URL = "http://binktest.com/atlas"

from app.audit import AuditLogger, sanitise  # noqa

standin = settings.AUDIT_SANITISATION_STANDIN


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

        result = sanitise(payload)
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
            payload={"type": "user", "details": {"username": "testuser", "password": "testpass"}},
            scheme_slug="test-scheme",
            handler_type=0,
            integration_service=0,
            message_uid=req_message_uid,
            record_uid=record_uid,
            channel="unit tests",
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
                    "payload": {"type": "user", "details": {"username": "testuser", "password": standin}},
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
