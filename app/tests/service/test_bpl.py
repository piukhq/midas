import json
import unittest
from unittest.mock import MagicMock

import httpretty

from app.agents.bpl import Bpl
from app.exceptions import GeneralError, AccountAlreadyExistsError, StatusRegistrationFailedError, NoSuchRecordError
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


class TestBPL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Bpl(*AGENT_CLASS_ARGUMENTS, scheme_slug="bpl-trenette")

    def test_join_happy_path(self):
        credentials = {"email": "bpluserf@binktest.com", "first_name": "BPL", "last_name": "Smith"}
        self.agent.join(credentials)

    @httpretty.activate
    def test_join_400(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {"display_message": "Malformed request.", "code": "MALFORMED_REQUEST"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=400)],
        )
        with self.assertRaises(GeneralError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_join_401(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {"display_message": "Supplied token is invalid.", "code": "INVALID_TOKEN"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=401)],
        )

        with self.assertRaises(GeneralError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_join_403(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {"display_message": "The requestor does not access to this retailer.", "code": "FORBIDDEN"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=403)],
        )

        with self.assertRaises(GeneralError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_join_409(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "It appears this account already exists.",
            "code": "ACCOUNT_EXISTS",
            "fields": ["email"],
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=409)],
        )

        with self.assertRaises(AccountAlreadyExistsError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Account already exists")

    @httpretty.activate
    def test_join_422_MISSING_FIELDS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Missing credentials from request.",
            "code": "MISSING_FIELDS",
            "fields": [
                "address_line1",
                "postcode",
            ],
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=422)],
        )

        with self.assertRaises(StatusRegistrationFailedError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Invalid credentials entered i.e password too short")

    @httpretty.activate
    def test_join_422_VALIDATION_FAILED(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "Submitted credentials did not pass validation.",
            "code": "VALIDATION_FAILED",
            "fields": [
                "email",
                "first_name",
                "last_name",
            ],
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=422)],
        )

        with self.assertRaises(StatusRegistrationFailedError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )
        self.assertEqual(e.exception.name, "Invalid credentials entered i.e password too short")

    @httpretty.activate
    def test_join_SERVICE_ERRORS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/enrolment"
        error_response = {
            "display_message": "The requestor does not access to this retailer.",
            "code": "any error will do",
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=500)],
        )

        with self.assertRaises(GeneralError) as e:
            self.agent.join(
                {
                    "email": "bpluserd@binktest.com",
                    "first_name": "BPL",
                    "last_name": "Smith",
                }
            )

        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_login_400(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {"display_message": "Malformed request.", "code": "MALFORMED_REQUEST"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=400)],
        )
        with self.assertRaises(GeneralError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_login_401(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {"display_message": "Supplied token is invalid.", "code": "INVALID_TOKEN"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=401)],
        )
        with self.assertRaises(GeneralError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_login_403(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {"display_message": "The requestor does not access to this retailer.", "code": "FORBIDDEN"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=403)],
        )
        with self.assertRaises(GeneralError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )
        self.assertEqual(e.exception.name, "General Error")

    @httpretty.activate
    def test_login_404(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {"display_message": "Account not found for provided credentials.", "code": "NO_ACCOUNT_FOUND"}

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=404)],
        )
        with self.assertRaises(NoSuchRecordError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )
        self.assertEqual(e.exception.name, "Account does not exist")

    @httpretty.activate
    def test_login_422_MISSING_FIELDS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {
            "display_message": "Missing credentials from request.",
            "code": "MISSING_FIELDS",
            "fields": [
                "address_line1",
                "postcode",
            ],
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=422)],
        )

        with self.assertRaises(StatusRegistrationFailedError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )
        self.assertEqual(e.exception.name, "Invalid credentials entered i.e password too short")

    @httpretty.activate
    def test_login_SERVICE_ERRORS(self):
        conf = MagicMock()
        conf.merchant_url = "https://api.dev.gb.bink.com/bpl/loyalty/trenette/accounts/getbycredentials"
        error_response = {
            "display_message": "The requestor does not access to this retailer.",
            "code": "any error will do",
        }

        httpretty.register_uri(
            httpretty.POST,
            conf.merchant_url,
            responses=[httpretty.Response(body=json.dumps(error_response), status=400)],
        )

        with self.assertRaises(GeneralError) as e:
            self.agent.login(
                {
                    "email": "bpluserd@binktest.com",
                    "card_number": "TRNT5665162796",
                }
            )

        self.assertEqual(e.exception.name, "General Error")


if __name__ == "__main__":
    unittest.main()
