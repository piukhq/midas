import json
import string
import unittest
from unittest.mock import patch

from app.agents.acteol_agents.wasabi import Wasabi


class TestWasabi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with unittest.mock.patch("app.agents.acteol.Configuration"):
            cls.mock_token = {
                "token": "abcde12345fghij",
                "timestamp": 123456789,
            }

            MOCK_AGENT_CLASS_ARGUMENTS = [
                1,
                {
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": None,
                    "credentials": {},
                },
            ]
            cls.wasabi = Wasabi(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="wasabi-club")

    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_refreshes_token(
        self, mock_store_token, mock_refresh_access_token, mock_token_is_valid,
    ):
        """
        The token is invalid and should be refreshed.
        """
        # GIVEN
        mock_token_is_valid.return_value = False

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)
        ):
            self.wasabi.authenticate()

            # THEN
            assert mock_refresh_access_token.called_once()
            assert mock_store_token.called_once_with(self.mock_token)

    @patch("app.agents.acteol.Acteol._token_is_valid")
    @patch("app.agents.acteol.Acteol._refresh_access_token")
    @patch("app.agents.acteol.Acteol._store_token")
    def test_does_not_refresh_token(
        self, mock_store_token, mock_refresh_access_token, mock_token_is_valid
    ):
        """
        The token is valid and should not be refreshed.
        """
        # GIVEN
        mock_token_is_valid.return_value = True

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "get", return_value=json.dumps(self.mock_token)
        ):
            token = self.wasabi.authenticate()

            # THEN
            assert not mock_refresh_access_token.called
            assert not mock_store_token.called
            assert token == self.mock_token

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

    def test_store_token(self):
        """
        Test that _store_token() calls the token store set method and returns an expected dict
        """
        # GIVEN
        mock_acteol_access_token = "abcde12345fghij"
        mock_current_timestamp = 123456789
        expected_token = {
            "token": mock_acteol_access_token,
            "timestamp": mock_current_timestamp,
        }

        # WHEN
        with unittest.mock.patch.object(
            self.wasabi.token_store, "set", return_value=True
        ):
            token = self.wasabi._store_token(
                acteol_access_token=mock_acteol_access_token,
                current_timestamp=mock_current_timestamp,
            )

            # THEN
            assert self.wasabi.token_store.set.called_once_with(
                self.wasabi.scheme_id, json.dumps(expected_token)
            )
            assert token == expected_token

    def test_make_headers(self):
        """
        Test that _make_headers returns a valid HTTP request authorization header
        """
        # GIVEN
        mock_acteol_access_token = "abcde12345fghij"
        expected_header = {"Authorization": f"Bearer {mock_acteol_access_token}"}

        # WHEN
        header = self.wasabi._make_headers(token=mock_acteol_access_token)

        # THEN
        assert header == expected_header

    def test_create_origin_id(self):
        """
        Test that _create_origin_id returns a hex string
        """
        # GIVEN
        user_email = "testperson@bink.com"
        origin_root = "Bink-Wasabi"

        # WHEN
        origin_id = self.wasabi._create_origin_id(
            user_email=user_email, origin_root=origin_root
        )

        # THEN
        assert all(c in string.hexdigits for c in origin_id)
