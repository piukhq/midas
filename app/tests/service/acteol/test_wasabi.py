import json
import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

import arrow
import httpretty
from app.agents import schemas
from app.agents.acteol_agents.wasabi import Wasabi
from app.agents.exceptions import LoginError, RegistrationError
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, CREDENTIALS


class TestWasabi(unittest.TestCase):
    @classmethod
    @patch("app.agents.acteol.Configuration")
    def setUpClass(cls, mock_config):
        conf = MagicMock()
        cls.credentials = CREDENTIALS["wasabi"]
        conf.merchant_url = cls.credentials["merchant_url"]
        mock_config.return_value = conf

        cls.wasabi = Wasabi(*AGENT_CLASS_ARGUMENTS)

    def test_login_has_token(self):
        """
        The attempt_login() method should result in a token
        """
        # WHEN
        self.wasabi.attempt_login(credentials=self.credentials)

        # THEN
        assert self.wasabi.token

    def test_refreshes_token(self):
        """
        Set the token timeout to a known value to retire it, and expect a new one to have been fetched
        """
        # GIVEN
        self.wasabi.AUTH_TOKEN_TIMEOUT = 0  # Force retire our token

        # WHEN
        self.wasabi.attempt_login(credentials=self.credentials)
        token_timestamp = arrow.get(self.wasabi.token["timestamp"])
        utc_now = arrow.utcnow()
        diff: timedelta = utc_now - token_timestamp

        # THEN
        assert diff.days == 0
        # A bit arbitrary, but should be less than 5 mins old, as it should have been refreshed
        assert diff.seconds < 300

    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_does_not_refresh_token(self, mock_store_token, mock_refresh_access_token):
        """
        Set the token timeout to a known value, the token should not have reached expiry and should not be refreshed
        """
        # GIVEN
        test_token = "abcdef123456"
        mock_refresh_access_token.return_value = test_token
        self.wasabi.AUTH_TOKEN_TIMEOUT = 0  # Force retire any current token

        # WHEN
        self.wasabi.attempt_login(credentials=self.credentials)

        # THEN
        assert mock_refresh_access_token.called_once()
        assert mock_store_token.called_once_with(test_token)

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
    @patch("app.agents.acteol_agents.Configuration")
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
    @patch("app.agents.acteol_agents.Configuration")
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
