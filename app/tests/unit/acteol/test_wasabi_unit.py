import unittest
from unittest.mock import MagicMock, patch

from app.agents.acteol_agents.wasabi import Wasabi
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


    @patch("app.agents.acteol.UserTokenStore")
    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_mocked_refreshes_token(
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
