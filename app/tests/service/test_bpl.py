import unittest
import json
import httpretty
from app.agents.bpl import Trenette
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS
from unittest.mock import MagicMock
from app.agents.exceptions import (AgentError, LoginError)


class TestBPL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Trenette(*AGENT_CLASS_ARGUMENTS, scheme_slug="bpl-trenette")

    def test_register_happy_path(self):
        credentials = {
            "email": "bpluserf@binktest.com",
            "first_name": "BPL",
            "last_name": "Smith"}
        self.agent.register(credentials)

    @httpretty.activate
    def test_register_400(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Malformed request.",
            "error": "MALFORMED_REQUEST"
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=400)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_register_401(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Supplied token is invalid.",
            "error": "INVALID_TOKEN"
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=401)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_register_403(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "The requestor does not access to this retailer.",
            "error": "FORBIDDEN"
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=403)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_register_409(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "It appears this account already exists.",
            "error": "ACCOUNT_EXISTS",
            "fields": [
                "email"
            ]
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=409)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Account already exists")

    @httpretty.activate
    def test_register_422_MISSING_FIELDS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Missing credentials from request.",
            "error": "MISSING_FIELDS",
            "fields": [
                "address_line1",
                "postcode",
            ]
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=422)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Invalid credentials entered i.e password too short")

    @httpretty.activate
    def test_register_422_VALIDATION_FAILED(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Submitted credentials did not pass validation.",
            "error": "VALIDATION_FAILED",
            "fields": [
                "email",
                "first_name",
                "last_name",
            ]
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=422)]
        )

        with self.assertRaises(LoginError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Invalid credentials entered i.e password too short")

    @httpretty.activate
    def test_register_SERVICE_ERRORS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "The requestor does not access to this retailer.",
            "error": "any error will do"
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=500)]
        )

        with self.assertRaises(AgentError) as e:
            self.agent.register(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )

        self.assertEqual(e.exception.name, "General Error")


if __name__ == "__main__":
    unittest.main()
