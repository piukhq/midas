import os
import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

import arrow
from app.agents.acteol_agents.wasabi import Wasabi
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


class TestWasabi(unittest.TestCase):
    @classmethod
    @patch("app.agents.acteol.Configuration")
    def setUpClass(cls, mock_config):
        mock_config_object = MagicMock()
        mock_config_object.merchant_url = "https://wasabiuat.wasabiworld.co.uk/"
        mock_config_object.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "username": os.environ.get("WASABI_USERNAME"),
                            "password": os.environ.get("WASABI_PASSWORD"),
                        }
                    }
                ]
            }
        }
        mock_config.return_value = mock_config_object

        cls.wasabi = Wasabi(*AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")

    def test_authenticate_has_token(self):
        """
        The attempt_authenticate() method should result in a token.
        """
        # WHEN
        self.wasabi.attempt_authenticate()

        # THEN
        assert self.wasabi.token

    def test_refreshes_token(self):
        """
        Set the token timeout to a known value to retire it, and expect a new one to have been fetched
        """
        # GIVEN
        self.wasabi.AUTH_TOKEN_TIMEOUT = 0  # Force retire our token

        # WHEN
        self.wasabi.attempt_authenticate()
        token_timestamp = arrow.get(self.wasabi.token["timestamp"])
        utc_now = arrow.utcnow()
        diff: timedelta = utc_now - token_timestamp

        # THEN
        assert diff.days == 0
        # A bit arbitrary, but should be less than 5 mins old, as it should have been refreshed
        assert diff.seconds < 300


if __name__ == "__main__":
    unittest.main()
