import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock
from unittest.mock import ANY, MagicMock, call

import arrow
import httpretty
from soteria.configuration import Configuration
from tenacity import wait_none

import app.agents.iceland
from app.agents.base import Balance
from app.agents.exceptions import AgentError, LoginError
from app.agents.iceland import Iceland
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus

credentials = {
    "card_number": "0000000000000000000",
    "last_name": "Smith",
    "postcode": "XX0 0XX",
}


class TestIcelandValidate(TestCase):
    def setUp(self) -> None:
        self.merchant_url = "https://reflector.dev.gb.bink.com/api/v1/bink/link"
        self.token_url = "https://reflector.dev.gb.bink.com/mock/oauth2/token"

        mock_configuration_object = MagicMock()
        mock_configuration_object.security_credentials = {
            "inbound": {"service": Configuration.OPEN_AUTH_SECURITY, "credentials": []},
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {
                            "payload": {
                                "client_id": "a_client_id",
                                "client_secret": "a_client_secret",
                                "grant_type": "client_credentials",
                                "resource": "a_resource",
                            },
                            "prefix": "Bearer",
                            "url": self.token_url,
                        },
                    }
                ],
            },
        }
        mock_configuration_object.merchant_url = self.merchant_url
        mock_configuration_object.callback_url = None

        with mock.patch("app.agents.iceland.Configuration", return_value=mock_configuration_object):
            # mock_user_token_store.get.return
            self.agent = Iceland(
                retry_count=1,
                user_info={
                    "scheme_account_id": 1,
                    "status": SchemeAccountStatus.WALLET_ONLY,
                    "journey_type": JourneyTypes.LINK.value,
                    "user_set": "1,2",
                    "credentials": credentials,
                },
                scheme_slug="iceland-bonus-card",
            )
            self.agent.integration_service = "ASYNC"
            self.agent._login.retry.wait = wait_none()  # type:ignore

    @httpretty.activate
    def test_refresh_token(self):
        httpretty.register_uri(
            httpretty.POST,
            self.token_url,
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=200)],
        )

        self.assertEqual(self.agent._refresh_token(), "a_token")

    def test_token_is_valid_true(self):
        token = {
            "iceland_access_token": "abcde12345fghij",
            "timestamp": (arrow.get(2022, 1, 1, 7, 0).int_timestamp,),
        }

        result = self.agent._token_is_valid(token, (arrow.get(2022, 1, 1, 7, 30).int_timestamp,))

        self.assertEqual(
            result,
            True,
        )

    def test_token_is_valid_false(self):
        token = {
            "iceland_access_token": "abcde12345fghij",
            "timestamp": (arrow.get(2022, 1, 1, 7, 0).int_timestamp,),
        }

        result = self.agent._token_is_valid(token, (arrow.get(2022, 1, 1, 8, 0).int_timestamp,))

        self.assertEqual(
            result,
            False,
        )

    def test_store_token(self):
        access_token = "abcde12345fghij"
        current_timestamp = arrow.get(2022, 1, 1, 7, 0).int_timestamp

        with mock.patch.object(self.agent.token_store, "set", return_value=True) as mock_token_store:
            self.agent._store_token(access_token, (current_timestamp,))

        self.assertEqual(
            mock_token_store.call_args[1]["token"],
            '{"iceland_access_token": "abcde12345fghij", "timestamp": [1641020400]}',
        )

    def test_authenticate_stored_token_valid(self):
        self.agent.token_store = MagicMock()
        self.agent.token_store.get.return_value = (
            f'{{"iceland_access_token": "abcde12345fghij", "timestamp": [{arrow.utcnow().int_timestamp}]}}'
        )
        token = self.agent._authenticate()
        self.assertEqual(self.agent.headers, {"Authorization": f"Bearer {'abcde12345fghij'}"})
        self.assertEqual(token, "abcde12345fghij")

    @mock.patch("app.agents.iceland.Iceland._refresh_token", return_value="")
    def test_authenticate_stored_token_expired(self, mock_refresh_token):
        self.agent.token_store = MagicMock()
        self.agent.token_store.get.return_value = (
            f'{{"iceland_access_token": "abcde12345fghij", "timestamp": [{arrow.utcnow().int_timestamp-3600}]}}'
        )
        self.agent._authenticate()
        mock_refresh_token.assert_called()

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.agent.login(credentials)
        self.assertIn("barcode", str(self.agent.user_info))
        self.assertEqual(self.agent._balance_amount, 10.0)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_bypasses_authentication_if_open_auth(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )
        self.agent.config.security_credentials["outbound"]["service"] = Configuration.OPEN_AUTH_SECURITY

        self.agent.login(credentials)
        self.assertEqual(0, mock_oath.call_count)

    def test_no_authentication_selected(self):
        self.agent.config.security_credentials["outbound"]["service"] = Configuration.RSA_SECURITY
        with self.assertRaises(AgentError) as e:
            self.agent.login(credentials)
        self.assertEqual("Configuration error", e.exception.name)
        self.assertEqual("Incorrect authorisation type specified", e.exception.message)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_401(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        with self.assertRaises(AgentError) as e:
            with self.assertRaises(LoginError):
                self.agent.login(credentials)

        self.assertEqual([e.exception.name, e.exception.code], ["An unknown error has occurred", 520])

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_validation_error_403(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "VALIDATION", "description": "Card owner details do not match"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(AgentError) as e:
            self.agent.login(credentials)
        self.assertEqual(e.exception.code, 403)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_card_number_error_436(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "CARD_NUMBER_ERROR", "description": "Card number not found"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(LoginError) as e:
            self.agent.login(credentials)
        self.assertEqual(e.exception.code, 436)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_link_limit_exceeded_437(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "LINK_LIMIT_EXCEEDED", "description": "Link limit exceeded"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(LoginError) as e:
            self.agent.login(credentials)
        self.assertEqual(e.exception.code, 437)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_link_limit_exceeded_438(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {
                            "error_codes": [
                                {"code": "CARD_NOT_REGISTERED", "description": "Card has not been registered"}
                            ]
                        }
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(LoginError) as e:
            self.agent.login(credentials)
        self.assertEqual(e.exception.code, 438)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    def test_login_200_link_limit_exceeded_439(self, mock_requests_session, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "GENERAL_ERROR", "description": "Unspecified exception"}]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(LoginError) as e:
            self.agent.login(credentials)
        self.assertEqual(e.exception.code, 439)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    def test_balance(self, mock_oauth):
        self.agent._balance_amount = amount = Decimal(10.0).quantize(TWO_PLACES)
        expected_result = Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )

        self.assertEqual(self.agent.balance(), expected_result)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_success_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.agent.login(credentials)

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.agent,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="ASYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.agent,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="ASYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.agent,
                slug="iceland-bonus-card",
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]
        expected_iceland_calls = [
            call("log-in-success"),
            call().send(self.agent, slug=self.agent.scheme_slug),
        ]

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls)
        self.assertEqual(3, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls)
        self.assertEqual(1, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_error_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"error_codes": [{"code": "VALIDATION", "description": "Card owner details do not match"}]}
                    ),
                    status=200,
                )
            ],
        )

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.agent,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="ASYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.agent,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=Configuration.VALIDATE_HANDLER,
                integration_service="ASYNC",
                status_code=HTTPStatus.OK,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.agent,
                slug="iceland-bonus-card",
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
        ]
        expected_iceland_calls = [
            call("log-in-fail"),
            call().send(self.agent, slug=self.agent.scheme_slug),
        ]

        with self.assertRaises(LoginError):
            self.agent.login(credentials)

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls[:6])
        self.assertEqual(9, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls[:2])
        self.assertEqual(3, mock_iceland_signal.call_count)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_401_failure_signals(self, mock_base_signal, mock_iceland_signal, mock_requests_session, mock_oauth):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        expected_base_calls = [
            call("send-audit-request"),
            call().send(
                self.agent,
                payload={
                    "card_number": ANY,
                    "last_name": "Smith",
                    "postcode": "XX0 0XX",
                    "message_uid": ANY,
                    "record_uid": ANY,
                    "callback_url": None,
                    "merchant_scheme_id1": ANY,
                    "merchant_scheme_id2": None,
                },
                scheme_slug="iceland-bonus-card",
                handler_type=2,
                integration_service="ASYNC",
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("send-audit-response"),
            call().send(
                self.agent,
                response=ANY,
                scheme_slug="iceland-bonus-card",
                handler_type=2,
                integration_service="ASYNC",
                status_code=401,
                message_uid=ANY,
                record_uid=ANY,
                channel="",
            ),
            call("record-http-request"),
            call().send(
                self.agent, slug="iceland-bonus-card", endpoint="/api/v1/bink/link", latency=ANY, response_code=401
            ),
            call("request-fail"),
            call().send(self.agent, slug="iceland-bonus-card", channel="", error="STATUS_LOGIN_FAILED"),
        ]
        expected_iceland_calls = [
            call("log-in-fail"),
            call().send(
                self.agent,
                slug=self.agent.scheme_slug,
            ),
        ]

        with self.assertRaises(AgentError):
            with self.assertRaises(LoginError):
                self.agent.login(credentials)

        self.assertEqual(expected_base_calls, mock_base_signal.mock_calls[:8])
        self.assertEqual(12, mock_base_signal.call_count)
        self.assertEqual(expected_iceland_calls, mock_iceland_signal.mock_calls[:2])
        self.assertEqual(3, mock_iceland_signal.call_count)
