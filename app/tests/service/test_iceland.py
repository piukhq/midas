import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, main, mock
from unittest.mock import ANY, MagicMock, call

import arrow
import httpretty
from tenacity import wait_none
from user_auth_token import UserTokenStore

from app.agents.base import Balance
from app.agents.exceptions import AgentError, LoginError
from app.agents.iceland import Iceland
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.scheme_account import TWO_PLACES
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE

cred = {
    "email": "testemail@testbink.com",
    "password": "testpassword",
}

credentials = {
    "card_number": "0000000000000000000",
    "last_name": "Smith",
    "postcode": "XX0 0XX",
}


class TestIcelandValidate(TestCase):
    def setUp(self) -> None:
        self.merchant_url = "https://customergateway-uat.iceland.co.uk/api/v1/bink/link"
        self.token_url = "https://reflector.dev.gb.bink.com/mock/api/v1/bink/link"

        mock_configuration_object = MagicMock()
        mock_configuration_object.security_credentials = {
            "inbound": {"service": 1, "credentials": []},
            "outbound": {
                "service": 2,
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

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        with mock.patch("app.agents.iceland.Configuration", return_value=mock_configuration_object):
            self.agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
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

    @mock.patch.object(UserTokenStore, "get")
    def test_authenticate_stored_token_valid(self, mock_token_store_get):
        mock_token_store_get.return_value = (
            f'{{"iceland_access_token": "abcde12345fghij", "timestamp": [{arrow.utcnow().int_timestamp}]}}'
        )
        token = self.agent._authenticate()
        self.assertEqual(token, "abcde12345fghij")

    @mock.patch("app.agents.iceland.Iceland._refresh_token", return_value="")
    @mock.patch.object(UserTokenStore, "get")
    def test_authenticate_stored_token_expired(self, mock_token_store_get, mock_refresh_token):
        mock_token_store_get.return_value = (
            f'{{"iceland_access_token": "abcde12345fghij", "timestamp": [{arrow.utcnow().int_timestamp-3600}]}}'
        )
        self.agent._authenticate()
        mock_refresh_token.assert_called()

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    def test_login_200(self, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.agent.login(credentials)
        self.assertEqual(self.agent.headers, {"Authorization": f"Bearer {'a_token'}"})
        self.assertIn("barcode", str(self.agent.user_info))
        self.assertEqual(self.agent._balance_amount, 10.0)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate")
    def test_login_bypasses_authentication_if_open_auth(self, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.agent.login(credentials)
        self.assertEqual(mock_oath.call_count, 0)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    def test_login_401(self, mock_oath):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        with self.assertRaises(LoginError) as e:
            self.agent.login(credentials)

        self.assertEqual(e.exception.name, "Invalid credentials")

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    def test_login_200_validation_error_403(self, mock_oath):
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
    def test_login_200_card_number_error_436(self, mock_oath):
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
    def test_login_200_link_limit_exceeded_437(self, mock_oath):
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
    def test_login_200_link_limit_exceeded_438(self, mock_oath):
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
    def test_login_200_link_limit_exceeded_439(self, mock_oath):
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
    @mock.patch("app.agents.iceland.signal", autospec=True)
    def test_login_success_signals(self, mock_signal, mock_oauth):
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        self.agent.login(credentials)

        expected_calls = [
            call("record-http-request"),
            call().send(
                self.agent,
                slug=self.agent.scheme_slug,
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
            call("log-in-success"),
            call().send(self.agent, slug=self.agent.scheme_slug),
        ]

        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("app.agents.iceland.signal", autospec=True)
    def test_login_error_signals(self, mock_signal, mock_oauth):
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

        expected_calls = [
            call("log-in-fail"),
            call().send(self.agent, slug=self.agent.scheme_slug),
            call("request-fail"),
            call().send(
                self.agent,
                slug=self.agent.scheme_slug,
                channel="",
                error="VALIDATION",
            ),
        ]

        with self.assertRaises(LoginError):
            self.agent.login(credentials)

        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._authenticate", return_value="a_token")
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_login_401_failure_signals(self, mock_signal, mock_oauth):
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        expected_calls = [
            call("request-fail"),
            call().send(
                self.agent,
                slug=self.agent.scheme_slug,
                channel="",
                error="STATUS_LOGIN_FAILED",
            ),
        ]

        with self.assertRaises(LoginError):
            self.agent.login(credentials)

        mock_signal.assert_has_calls(expected_calls)


class TestIcelandMerchantIntegration(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS, scheme_slug="iceland-bonus-card")
        cls.i.attempt_login(cred)

    def test_fetch_balance(self):
        balance = self.i.balance()
        self.assertIsNotNone(balance)

    def test_transactions(self):
        transactions = self.i.transactions()
        self.assertIsNotNone(transactions)


class TestIcelandMerchantIntegrationValidate(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        credentials = cred
        credentials.pop("merchant_identifier", None)

        cls.i.attempt_login(cred)

    def test_validate(self):
        balance = self.i.balance()
        self.assertIsNotNone(balance)


class TestIcelandMerchantIntegrationFail(TestCase):
    def test_login_fail(self):
        i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        credentials = cred
        credentials["last_name"] = "midastest"
        credentials.pop("merchant_identifier", None)
        with self.assertRaises(LoginError) as e:
            i.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == "__main__":
    main()
