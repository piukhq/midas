import json
import unittest
from unittest.mock import patch, MagicMock

import httpretty

from app.agents import schemas
from app.agents.ecrebo import FatFace, BurgerKing, WhSmith
from app.agents.exceptions import LoginError, RegistrationError
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS

cred = {
    "email": "testuser5@bink.com",
    "first_name": "test",
    "last_name": "user",
    "consents": [{"slug": "email_marketing", "value": "true"}],
}


class TestEcrebo(unittest.TestCase):
    @classmethod
    @patch("app.agents.ecrebo.Configuration")
    def setUpClass(cls, mock_config):
        conf = MagicMock()
        conf.merchant_url = "https://virtserver.swaggerhub.com/Bink_API/ecrebo-bink_integration/1.0.0"
        conf.security_credentials = {
            "outbound": {
                "credentials": [{"value": {"username": "fatface_external_staging", "password": "c5tzCv5ms2k8eFR6"}}]
            }
        }
        mock_config.return_value = conf

        cls.agents = [agent_class(*AGENT_CLASS_ARGUMENTS) for agent_class in (FatFace, BurgerKing, WhSmith)]

        for agent in cls.agents:
            agent.register(cred)
            agent.login(agent.user_info["credentials"])

    def test_login(self):
        for agent in self.agents:
            self.assertIsNotNone(agent.identifier)

    def test_transactions(self):
        for agent in self.agents:
            transactions = agent.transactions()
            self.assertIsNotNone(transactions)
            schemas.transactions(transactions)

    def test_balance(self):
        for agent in self.agents:
            balance = agent.balance()
            schemas.balance(balance)

    @httpretty.activate
    @patch("app.agents.ecrebo.Configuration")
    def test_login_404(self, mock_config):
        conf = MagicMock()
        conf.merchant_url = "http://ecrebo.test"
        conf.security_credentials = {
            "outbound": {
                "credentials": [{"value": {"username": "fatface_external_staging", "password": "c5tzCv5ms2k8eFR6"}}]
            }
        }
        mock_config.return_value = conf

        httpretty.register_uri(
            httpretty.POST, f"{conf.merchant_url}/v1/auth/login", body=json.dumps({"token": "test-api-token"})
        )

        agent = FatFace(*AGENT_CLASS_ARGUMENTS)
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

    @httpretty.activate
    @patch("app.agents.ecrebo.Configuration")
    def test_register_409(self, mock_config):
        conf = MagicMock()
        conf.merchant_url = "http://ecrebo.test"
        conf.security_credentials = {
            "outbound": {
                "credentials": [{"value": {"username": "fatface_external_staging", "password": "c5tzCv5ms2k8eFR6"}}]
            }
        }
        mock_config.return_value = conf

        httpretty.register_uri(
            httpretty.POST, f"{conf.merchant_url}/v1/auth/login", body=json.dumps({"token": "test-api-token"})
        )

        agent = FatFace(*AGENT_CLASS_ARGUMENTS)
        retailer_id = agent.RETAILER_ID

        httpretty.register_uri(
            httpretty.POST, f"{conf.merchant_url}/v1/list/append_item/{retailer_id}/assets/membership", status=409
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
