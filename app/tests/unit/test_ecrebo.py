import json
import unittest
from http import HTTPStatus
from unittest.mock import ANY, MagicMock, call, patch

import httpretty
from app.agents.ecrebo import WhSmith
from requests import HTTPError


class TestEcrebo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with unittest.mock.patch("app.agents.ecrebo.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = {
                "outbound": {
                    "credentials": [
                        {
                            "value": {
                                "username": "some_user",
                                "password": "some_pass",
                            }
                        }
                    ]
                }
            }
            mock_configuration.return_value = mock_config_object
            MOCK_AGENT_CLASS_ARGUMENTS = [
                1,
                {
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": None,
                    "credentials": {},
                    "channel": "com.bink.wallet",
                },
            ]
            cls.whsmith = WhSmith(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="whsmith-rewards")
            cls.whsmith.base_url = "https://london-capi-test.ecrebo.com"

    @httpretty.activate
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_authenticate_calls_signal_with_error(self, mock_signal):
        """
        Check that correct params are passed to signal on HTTPError
        """
        # GIVEN
        login_path = "/v1/auth/login"
        httpretty.register_uri(
            httpretty.POST, f"{self.whsmith.base_url}{login_path}", status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=login_path, latency=ANY,
                        response_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                        slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.assertRaises(HTTPError, self.whsmith._authenticate)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_authenticate_calls_signal(self, mock_signal):
        """
        Check that correct params are passed to signal
        """
        # GIVEN
        mock_token = "amocktokenstring"
        login_path = "/v1/auth/login"
        httpretty.register_uri(
            httpretty.POST,
            f"{self.whsmith.base_url}{login_path}",
            responses=[httpretty.Response(body=json.dumps({"token": mock_token}))],
            status=HTTPStatus.OK,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=login_path, latency=ANY,
                        response_code=HTTPStatus.OK,
                        slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        token = self.whsmith._authenticate()

        # THEN
        mock_signal.assert_has_calls(expected_calls)
        assert token == mock_token
