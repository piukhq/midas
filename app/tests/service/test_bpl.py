import unittest
import json
import httpretty
from app.agents.bpl import Trenette
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, CREDENTIALS
from unittest.mock import patch, MagicMock
from app.agents.exceptions import (
    AgentError, LoginError, RegistrationError,
    GENERAL_ERROR,
    ACCOUNT_ALREADY_EXISTS,
)


class TestBPL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Trenette(*AGENT_CLASS_ARGUMENTS, scheme_slug="bpl-trenette")

    def test_register_happy_path(self):
        credentials = {
            "email": "bpluserc@binktest.com",
            "first_name": "BPL",
            "last_name": "Smith"}
        self.agent.register(credentials)

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


if __name__ == "__main__":
    unittest.main()



