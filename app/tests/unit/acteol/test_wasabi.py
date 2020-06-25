import unittest
from unittest.mock import MagicMock, patch

from app.agents.acteol_agents.wasabi import Wasabi
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


class TestWasabi(unittest.TestCase):
    @classmethod
    @patch("app.agents.acteol.Configuration")
    def setUpClass(cls, mock_config):
        conf = MagicMock()
        cls.credentials = {
            "merchant_url": "https://test.wasabiuat.wasabiworld.co.uk/",
            "email": "testuser@bink.com",
            "first_name": "test",
            "last_name": "user",
            "password": "$F9eA*RY",
            "postcode": "AA00 0AA",
            "phone": "00000000000",
            "consents": [{"slug": "email_marketing", "value": True}],
        }
        conf.merchant_url = cls.credentials["merchant_url"]
        mock_config.return_value = conf

        cls.wasabi = Wasabi(*AGENT_CLASS_ARGUMENTS)

    @patch("app.agents.acteol.UserTokenStore")
    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_refreshes_token(
        self,
        mock_store_token,
        mock_refresh_access_token,
        mock_token_is_valid,
        mock_user_token_store,
    ):
        """
        The token is invalid and should be refreshed.
        """
        # GIVEN
        mock_token = {
            "token": "abcde12345fghij",
            "timestamp": 123456789,
        }
        mock_user_token_store.return_value.get.return_value = mock_token
        mock_token_is_valid.return_value = False

        # WHEN
        self.wasabi.attempt_login(credentials=self.credentials)

        # THEN
        assert mock_refresh_access_token.called_once()
        assert mock_store_token.called_once_with(mock_token)

    @patch("app.agents.acteol.UserTokenStore")
    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_does_not_refresh_token(
        self,
        mock_store_token,
        mock_refresh_access_token,
        mock_token_is_valid,
        mock_user_token_store,
    ):
        """
        The token is valid and should not be refreshed.
        """
        # GIVEN
        mock_token = {
            "token": "abcde12345fghij",
            "timestamp": 123456789,
        }
        mock_user_token_store.return_value.get.return_value = mock_token
        mock_token_is_valid.return_value = True

        # WHEN
        self.wasabi.attempt_login(credentials=self.credentials)

        # THEN
        assert not mock_refresh_access_token.called
        assert not mock_store_token.called

    def test_token_is_valid_false_for_just_expired(self):
        """
        Test that _token_is_valid() returns false when we have exactly reached the expiry
        """

        # GIVEN
        mock_current_timestamp = 75700
        mock_auth_token_timeout = 75600  # 21 hours, our cutoff point, is 75600 seconds
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "token": "abcde12345fghij",
            "timestamp": 100,  # an easy number to work with to get 75600
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is False

    def test_token_is_valid_false_for_expired(self):
        """
        Test that _token_is_valid() returns false when we have a token past its expiry
        """

        # GIVEN
        mock_current_timestamp = 10000
        mock_auth_token_timeout = 1  # Expire tokens after 1 second
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "token": "abcde12345fghij",
            "timestamp": 10,  # an easy number to work with to exceed the timout setting
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is False

    def test_token_is_valid_true_for_valid(self):
        """
        Test that _token_is_valid() returns true when the token is well within validity
        """

        # GIVEN
        mock_current_timestamp = 1000
        mock_auth_token_timeout = 900  # Expire tokens after 15 minutes
        self.wasabi.AUTH_TOKEN_TIMEOUT = mock_auth_token_timeout
        mock_token = {
            "token": "abcde12345fghij",
            "timestamp": 450,  # an easy number to work with to stay within validity range
        }

        # WHEN
        is_valid = self.wasabi._token_is_valid(
            token=mock_token, current_timestamp=mock_current_timestamp
        )

        # THEN
        assert is_valid is True
