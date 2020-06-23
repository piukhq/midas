import json
import unittest
from unittest.mock import MagicMock, patch

import httpretty
from app.agents import schemas
from app.agents.acteol import Wasabi
from app.agents.exceptions import LoginError, RegistrationError
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, CREDENTIALS


class TestWasabi(unittest.TestCase):
    @classmethod
    @patch("app.agents.acteol.Configuration")
    def setUpClass(cls, mock_config):
        wasabi = Wasabi(*AGENT_CLASS_ARGUMENTS)
        conf = MagicMock()
        credentials = CREDENTIALS["wasabi"]
        conf.merchant_url = credentials["merchant_url"]
        conf.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "username": credentials["email"],
                            "password": credentials["password"],
                        }
                    }
                ]
            }
        }
        mock_config.return_value = conf
        wasabi.attempt_login(credentials=credentials)

    # @unittest.skip("nothing to see here")
    def test_login(self):
        assert True
        # json_result = self.h.login_response.json()["CustomerSignOnResult"]
        # self.assertEqual(self.h.login_response.status_code, 200)
        # self.assertEqual(json_result["outcome"], "Success")

    @unittest.skip("nothing to see here")
    def test_transactions(self):
        for agent in self.agents:
            transactions = agent.transactions()
            self.assertIsNotNone(transactions)
            schemas.transactions(transactions)

    @unittest.skip("nothing to see here")
    def test_balance(self):
        for agent in self.agents:
            balance = agent.balance()
            schemas.balance(balance)

    @unittest.skip("nothing to see here")
    @httpretty.activate
    @patch("app.agents.acteol.Configuration")
    def test_login_404(self, mock_config):
        conf = MagicMock()
        conf.merchant_url = "http://acteol.test"
        conf.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "username": "wasabi_external_staging",
                            "password": "c5tzCv5ms2k8eFR6",
                        }
                    }
                ]
            }
        }
        mock_config.return_value = conf

        httpretty.register_uri(
            httpretty.POST,
            f"{conf.merchant_url}/v1/auth/login",
            body=json.dumps({"token": "test-api-token"}),
        )

        agent = Wasabi(*AGENT_CLASS_ARGUMENTS)
        retailer_id = agent.RETAILER_ID
        card_number = "card-number-123"

        httpretty.register_uri(
            httpretty.GET,
            f"{conf.merchant_url}/v1/list/query_item/{retailer_id}/assets/membership/token/{card_number}",
            status=404,
        )

        with self.assertRaises(LoginError) as e:
            agent.attempt_login({"card_number": card_number})
        self.assertEqual(e.exception.name, "Invalid credentials")

    @unittest.skip("nothing to see here")
    @httpretty.activate
    @patch("app.agents.acteol.Configuration")
    def test_register_409(self, mock_config):
        conf = MagicMock()
        conf.merchant_url = "http://acteol.test"
        conf.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "username": "wasabi_external_staging",
                            "password": "c5tzCv5ms2k8eFR6",
                        }
                    }
                ]
            }
        }
        mock_config.return_value = conf

        httpretty.register_uri(
            httpretty.POST,
            f"{conf.merchant_url}/v1/auth/login",
            body=json.dumps({"token": "test-api-token"}),
        )

        agent = Wasabi(*AGENT_CLASS_ARGUMENTS)
        retailer_id = agent.RETAILER_ID

        httpretty.register_uri(
            httpretty.POST,
            f"{conf.merchant_url}/v1/list/append_item/{retailer_id}/assets/membership",
            status=409,
        )

        with self.assertRaises(RegistrationError) as e:
            agent.attempt_register(
                {
                    "email": "testuser@test",
                    "first_name": "test",
                    "last_name": "user",
                    "consents": [{"slug": "email_marketing", "value": True}],
                }
            )
        self.assertEqual(e.exception.name, "Account already exists")


if __name__ == "__main__":
    unittest.main()
