import json
import unittest
from http import HTTPStatus
from unittest.mock import ANY, MagicMock, call, patch
from uuid import uuid4

import httpretty
from app.agents.ecrebo import WhSmith
from app.agents.exceptions import LoginError, RegistrationError
from requests import HTTPError


class TestEcreboSignal(unittest.TestCase):
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
                    "credentials": {
                        "email": "mrtestman@thing.com",
                        "title": "Mr",
                        "first_name": "Test",
                        "last_name": "Man",
                        "phone": 1234567890,
                        "address_1": "1 The Street",
                        "town_city": "Nowhereton",
                        "postcode": "NW11NW",
                    },
                    "channel": "com.bink.wallet",
                },
            ]
            cls.whsmith = WhSmith(*MOCK_AGENT_CLASS_ARGUMENTS, scheme_slug="whsmith-rewards")
            cls.whsmith.base_url = "https://london-capi-test.ecrebo.com"

    @httpretty.activate
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_authenticate_calls_signal_on_error(self, mock_signal):
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
        Check that correct params are passed to signal when the HTTP request is OK
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

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_signals(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals when the call is OK
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/someendpoint"
        mock_membership_data = {"username": "Mr A User"}
        httpretty.register_uri(
            httpretty.GET,
            f"{self.whsmith.base_url}{mock_endpoint}",
            responses=[httpretty.Response(body=json.dumps({"data": mock_membership_data}))],
            status=HTTPStatus.OK,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY, response_code=HTTPStatus.OK,
                        slug=self.whsmith.scheme_slug),

            call("log-in-success"),
            call().send(self.whsmith, slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        membership_data = self.whsmith._get_membership_data(endpoint=mock_endpoint)

        # THEN
        mock_signal.assert_has_calls(expected_calls)
        assert membership_data == mock_membership_data

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_signals_on_error(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals on HTTPError
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/somebrokenendpoint"
        mock_api_url = f"{self.whsmith.base_url}{mock_endpoint}"
        httpretty.register_uri(
            httpretty.GET,
            mock_api_url,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY,
                        response_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                        slug=self.whsmith.scheme_slug),
            call("log-in-fail"),
            call().send(self.whsmith, slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.assertRaises(HTTPError, self.whsmith._get_membership_data, endpoint=mock_endpoint)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_signals_and_raises_login_error(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals and a login error is raised when the HTTP request returns 404
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/somebrokenendpoint"
        mock_api_url = f"{self.whsmith.base_url}{mock_endpoint}"
        httpretty.register_uri(
            httpretty.GET,
            mock_api_url,
            status=HTTPStatus.NOT_FOUND,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY,
                        response_code=HTTPStatus.NOT_FOUND,
                        slug=self.whsmith.scheme_slug),
            call("log-in-fail"),
            call().send(self.whsmith, slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.assertRaises(LoginError, self.whsmith._get_membership_data, endpoint=mock_endpoint)

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_register_calls_signals_success(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a successful registration
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_get_card_number_and_uid.return_value = (987654321, str(uuid4()))
        mock_endpoint = f"/v1/list/append_item/{self.whsmith.RETAILER_ID}/assets/membership"
        mock_api_url = f"{self.whsmith.base_url}{mock_endpoint}"
        httpretty.register_uri(
            httpretty.POST,
            mock_api_url,
            responses=[httpretty.Response(body=json.dumps({"publisher": [{"message": "testingonetwothree"}]}))],
            status=HTTPStatus.OK,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY, response_code=HTTPStatus.OK,
                        slug=self.whsmith.scheme_slug),
            call("register-success"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.whsmith.register(credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_register_calls_signals_for_409(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a CONFLICT (409) response during registration
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_get_card_number_and_uid.return_value = (987654321, str(uuid4()))
        mock_endpoint = f"/v1/list/append_item/{self.whsmith.RETAILER_ID}/assets/membership"
        mock_api_url = f"{self.whsmith.base_url}{mock_endpoint}"
        httpretty.register_uri(
            httpretty.POST,
            mock_api_url,
            status=HTTPStatus.CONFLICT,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY, response_code=HTTPStatus.CONFLICT,
                        slug=self.whsmith.scheme_slug),
            call("register-fail"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.assertRaises(RegistrationError, self.whsmith.register, credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_register_calls_signals_for_httperror(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a HTTPError response during registration
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_get_card_number_and_uid.return_value = (987654321, str(uuid4()))
        mock_endpoint = f"/v1/list/append_item/{self.whsmith.RETAILER_ID}/assets/membership"
        mock_api_url = f"{self.whsmith.base_url}{mock_endpoint}"
        httpretty.register_uri(
            httpretty.POST,
            mock_api_url,
            status=HTTPStatus.GATEWAY_TIMEOUT,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(self.whsmith, endpoint=mock_endpoint, latency=ANY, response_code=HTTPStatus.GATEWAY_TIMEOUT,
                        slug=self.whsmith.scheme_slug),
            call("register-fail"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug)
        ]

        # WHEN
        self.assertRaises(HTTPError, self.whsmith.register, credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)
