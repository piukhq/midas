import json
import unittest
from http import HTTPStatus
from unittest.mock import ANY, MagicMock, call, patch
from uuid import uuid4

import httpretty
from requests import HTTPError, RequestException

from app.agents.ecrebo import FatFace, WhSmith
from app.agents.exceptions import ACCOUNT_ALREADY_EXISTS, JoinError, LoginError


class TestEcreboSignal(unittest.TestCase):
    fatface: FatFace
    whsmith: WhSmith

    @classmethod
    def setUp(cls) -> None:
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

            cls.fatface = FatFace(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": 2,
                    "credentials": {
                        "email": "mrfatface@ecrebo.com",
                        "first_name": "Test",
                        "last_name": "FatFace",
                        "join_date": "2021/02/24",
                        "card_number": "1234567",
                        "consents": [{"slug": "email_marketing", "value": True}],
                    },
                    "channel": "com.bink.wallet",
                },
                scheme_slug="fatface",
            )
            cls.whsmith = WhSmith(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": 1,
                    "user_set": "1,2",
                    "journey_type": 1,
                    "credentials": {
                        "email": "mrtestman@thing.com",
                        "title": "Mr",
                        "first_name": "Test",
                        "last_name": "Man",
                        "phone": 1234567890,
                        "address_1": "1 The Street",
                        "town_city": "Nowhereton",
                        "postcode": "NW11NW",
                        "card_number": "1234567",
                    },
                    "channel": "com.bink.wallet",
                },
                scheme_slug="whsmith-rewards",
            )
            cls.fatface.base_url = "https://london-capi-test.ecrebo.com"
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
            httpretty.POST,
            f"{self.whsmith.base_url}{login_path}",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(
                self.whsmith,
                endpoint=login_path,
                latency=ANY,
                response_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                slug=self.whsmith.scheme_slug,
            ),
            call("request-fail"),
            call().send(
                self.whsmith, channel=self.whsmith.channel, error="Internal Server Error", slug=self.whsmith.scheme_slug
            ),
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
            call().send(
                self.whsmith,
                endpoint=login_path,
                latency=ANY,
                response_code=HTTPStatus.OK,
                slug=self.whsmith.scheme_slug,
            ),
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
        mock_membership_data = '{"data": {"data": {"username": "Mr A User"}}}'
        httpretty.register_uri(
            httpretty.GET,
            f"{self.whsmith.base_url}{mock_endpoint}",
            responses=[httpretty.Response(body=json.dumps({"data": mock_membership_data}))],
            status=HTTPStatus.OK,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("record-http-request"),
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.OK,
                slug=self.whsmith.scheme_slug,
            ),
        ]

        # WHEN
        membership_data = self.whsmith._get_membership_response(
            endpoint=mock_endpoint, journey_type=self.whsmith.user_info["journey_type"]
        )

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
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                slug=self.whsmith.scheme_slug,
            ),
            call("request-fail"),
            call().send(
                self.whsmith, channel=self.whsmith.channel, error="Internal Server Error", slug=self.whsmith.scheme_slug
            ),
        ]

        # WHEN
        self.assertRaises(
            HTTPError,
            self.whsmith._get_membership_response,
            endpoint=mock_endpoint,
            journey_type=self.whsmith.user_info["journey_type"],
        )

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
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.NOT_FOUND,
                slug=self.whsmith.scheme_slug,
            ),
        ]

        # WHEN
        self.assertRaises(
            LoginError,
            self.whsmith._get_membership_response,
            endpoint=mock_endpoint,
            journey_type=self.whsmith.user_info["journey_type"],
        )

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_audit_add_response(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals when the call is OK
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/someendpoint"
        mock_membership_data = '{"data": {"data": {"username": "Mr A User"}}}'
        httpretty.register_uri(
            httpretty.GET,
            f"{self.whsmith.base_url}{mock_endpoint}",
            responses=[httpretty.Response(body=json.dumps({"data": mock_membership_data}))],
            status=HTTPStatus.OK,
        )

        # WHEN
        membership_data = self.whsmith._get_membership_response(
            endpoint=mock_endpoint, journey_type=self.whsmith.user_info["journey_type"], from_login=True
        )

        # THEN
        assert mock_signal.called
        assert membership_data == mock_membership_data

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_audit_add_response_on_http_error(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals when the call is OK
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/someendpoint"
        httpretty.register_uri(
            httpretty.GET,
            f"{self.whsmith.base_url}{mock_endpoint}",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        # WHEN
        self.assertRaises(
            HTTPError,
            self.whsmith._get_membership_response,
            endpoint=mock_endpoint,
            journey_type=self.whsmith.user_info["journey_type"],
            from_login=True,
        )

        # THEN
        assert mock_signal.called

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_get_membership_data_calls_audit_add_response_on_requests_exceptions(self, mock_signal, mock_authenticate):
        """
        Check that correct params are passed to signals when the call is OK
        """
        # GIVEN
        mock_token = "amocktokenstring"
        mock_authenticate.return_value = mock_token
        mock_endpoint = "/v1/someendpoint"
        httpretty.register_uri(
            httpretty.GET,
            f"{self.whsmith.base_url}{mock_endpoint}",
            status=HTTPStatus.GATEWAY_TIMEOUT,
        )

        # WHEN
        self.assertRaises(
            RequestException,
            self.whsmith._get_membership_response,
            endpoint=mock_endpoint,
            journey_type=self.whsmith.user_info["journey_type"],
            from_login=True,
        )

        # THEN
        assert mock_signal.called

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_join_calls_signals_success(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a successful join
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
        audit_payload = {
            "data": {
                "email": "mrtestman@thing.com",
                "title": "Mr",
                "first_name": "Test",
                "surname": "Man",
                "mobile_number": 1234567890,
                "address_line1": "1 The Street",
                "city": "Nowhereton",
                "postcode": "NW11NW",
                "validated": True,
            }
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("send-audit-request"),
            call().send(
                payload=audit_payload,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("record-http-request"),
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.OK,
                slug=self.whsmith.scheme_slug,
            ),
            call("send-audit-response"),
            call().send(
                response=ANY,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("join-success"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug),
        ]

        # WHEN
        self.whsmith.join(credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_join_calls_signals_for_409(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a CONFLICT (409) response during join
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
        audit_payload = {
            "data": {
                "email": "mrtestman@thing.com",
                "title": "Mr",
                "first_name": "Test",
                "surname": "Man",
                "mobile_number": 1234567890,
                "address_line1": "1 The Street",
                "city": "Nowhereton",
                "postcode": "NW11NW",
                "validated": True,
            }
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("send-audit-request"),
            call().send(
                payload=audit_payload,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("record-http-request"),
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.CONFLICT,
                slug=self.whsmith.scheme_slug,
            ),
            call("send-audit-response"),
            call().send(
                response=ANY,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                status_code=HTTPStatus.CONFLICT,
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("join-fail"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug),
            call("request-fail"),
            call().send(
                self.whsmith, channel=self.whsmith.channel, error=ACCOUNT_ALREADY_EXISTS, slug=self.whsmith.scheme_slug
            ),
        ]

        # WHEN
        self.assertRaises(JoinError, self.whsmith.join, credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_card_number_and_uid")
    @patch("app.agents.ecrebo.Ecrebo._authenticate")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_join_calls_signals_for_httperror(self, mock_signal, mock_authenticate, mock_get_card_number_and_uid):
        """
        Check that correct params are passed to the signals for a HTTPError response during join
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
        audit_payload = {
            "data": {
                "email": "mrtestman@thing.com",
                "title": "Mr",
                "first_name": "Test",
                "surname": "Man",
                "mobile_number": 1234567890,
                "address_line1": "1 The Street",
                "city": "Nowhereton",
                "postcode": "NW11NW",
                "validated": True,
            }
        }
        expected_calls = [  # The expected call stack for signal, in order
            call("send-audit-request"),
            call().send(
                payload=audit_payload,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("record-http-request"),
            call().send(
                self.whsmith,
                endpoint=mock_endpoint,
                latency=ANY,
                response_code=HTTPStatus.GATEWAY_TIMEOUT,
                slug=self.whsmith.scheme_slug,
            ),
            call("send-audit-response"),
            call().send(
                response=ANY,
                scheme_slug=self.whsmith.scheme_slug,
                handler_type=1,
                integration_service="SYNC",
                status_code=HTTPStatus.GATEWAY_TIMEOUT,
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("join-fail"),
            call().send(self.whsmith, channel=self.whsmith.user_info["channel"], slug=self.whsmith.scheme_slug),
            call("request-fail"),
            call().send(
                self.whsmith, channel=self.whsmith.channel, error="Gateway Timeout", slug=self.whsmith.scheme_slug
            ),
        ]

        # WHEN
        self.assertRaises(HTTPError, self.whsmith.join, credentials=self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.ecrebo.Ecrebo._get_membership_response")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_login_calls_signals(self, mock_signal, mock_get_membership_response):
        """
        Check that correct params are passed to signals when the login is successful
        """
        # GIVEN
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-success"),
            call().send(self.whsmith, slug=self.whsmith.scheme_slug),
        ]

        # WHEN
        self.whsmith.login(self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @patch("app.agents.ecrebo.Ecrebo._get_membership_response", side_effect=HTTPError)
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_login_does_not_call_signal_on_exception(self, mock_signal, mock_get_membership_response):
        """
        Check that correct params are passed to signals when the login is successful
        """
        # GIVEN
        expected_calls = [  # The expected call stack for signal, in order
            call("log-in-fail"),
            call().send(self.whsmith, slug=self.whsmith.scheme_slug),
        ]

        # WHEN
        self.assertRaises(HTTPError, self.whsmith.login, self.whsmith.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @patch("app.agents.ecrebo.Ecrebo._get_membership_response")
    @patch("app.agents.ecrebo.signal", autospec=True)
    def test_login_fatface(self, mock_signal, mock_get_membership_response):
        """
        Testing FatFace login journey to ensure audit request/responses are created
        """
        # GIVEN
        path = "/v1/list/query_item/"
        card_number = "1234567"

        httpretty.register_uri(
            httpretty.GET,
            f"{self.fatface.base_url}{path}{self.fatface.RETAILER_ID}/assets/membership/token/{card_number}",
            status=HTTPStatus.OK,
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("send-audit-request"),
            call().send(
                payload={"card_number": "1234567"},
                scheme_slug=self.fatface.scheme_slug,
                handler_type=2,
                integration_service="SYNC",
                message_uid=ANY,
                record_uid=ANY,
            ),
            call("log-in-success"),
            call().send(self.fatface, slug=self.fatface.scheme_slug),
        ]
        # WHEN
        self.fatface.login(credentials=self.fatface.user_info["credentials"])

        # THEN
        mock_signal.assert_has_calls(expected_calls)
