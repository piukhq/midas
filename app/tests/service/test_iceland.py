import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, main, mock
from unittest.mock import ANY, MagicMock, call

import httpretty
from tenacity import wait_none

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


# Needs to be renamed to TestIceland once it has replaced the existing class TestIceland
class TestIceland(TestCase):
    def mock_link_configuration_object(self):
        self.merchant_url = "https://customergateway-uat.iceland.co.uk/api/v1/bink/link"
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
                            "url": "https://reflector.dev.gb.bink.com/mock/api/v1/bink/link",
                        },
                    }
                ],
            },
        }

        mock_configuration_object.merchant_url = self.merchant_url
        mock_configuration_object.callback_url = None
        return mock_configuration_object

    @httpretty.activate
    @mock.patch("app.agents.iceland.Configuration")
    def test_get_oauth_token(self, mock_configuration):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            httpretty.POST,
            "https://reflector.dev.gb.bink.com/mock/api/v1/bink/link",
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=200)],
        )

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")

        self.assertEqual(agent._refresh_oauth_token(), "a_token")

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")

        agent.login(credentials)
        self.assertEqual(agent.headers, {"Authorization": f"Bearer {'a_token'}"})
        self.assertIn("barcode", str(agent.user_info))
        self.assertEqual(agent._balance_amount, 10.0)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_401(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(LoginError) as e:
            agent.login(credentials)

        self.assertEqual(e.exception.name, "Invalid credentials")

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_validation_error_403(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(AgentError) as e:
            agent.login(credentials)
        self.assertEqual(e.exception.code, 403)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_card_number_error_436(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(LoginError) as e:
            agent.login(credentials)
        self.assertEqual(e.exception.code, 436)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_link_limit_exceeded_437(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()

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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(LoginError) as e:
            agent.login(credentials)
        self.assertEqual(e.exception.code, 437)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_link_limit_exceeded_438(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(LoginError) as e:
            agent.login(credentials)
        self.assertEqual(e.exception.code, 438)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_link_limit_exceeded_439(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        with self.assertRaises(LoginError) as e:
            agent.login(credentials)
        self.assertEqual(e.exception.code, 439)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_balance(self, mock_configuration):
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._balance_amount = amount = Decimal(10.0).quantize(TWO_PLACES)
        expected_result = Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )

        self.assertEqual(agent.balance(), expected_result)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_success_signals(self, mock_configuration, mock_signal, mock_oauth):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            httpretty.POST,
            self.merchant_url,
            responses=[httpretty.Response(body=json.dumps({"balance": 10.0}), status=200)],
        )

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent.login(credentials)

        expected_calls = [
            call("record-http-request"),
            call().send(
                agent,
                slug=agent.scheme_slug,
                endpoint="/api/v1/bink/link",
                latency=ANY,
                response_code=HTTPStatus.OK,
            ),
            call("log-in-success"),
            call().send(agent, slug=agent.scheme_slug),
        ]

        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.signal", autospec=True)
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_error_signals(self, mock_configuration, mock_signal, mock_oauth):
        mock_configuration.return_value = self.mock_link_configuration_object()
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

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")

        expected_calls = [
            call("log-in-fail"),
            call().send(agent, slug=agent.scheme_slug),
            call("request-fail"),
            call().send(
                agent,
                slug=agent.scheme_slug,
                channel="",
                error="VALIDATION",
            ),
        ]

        with self.assertRaises(LoginError):
            agent.login(credentials)

        mock_signal.assert_has_calls(expected_calls)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.base.signal", autospec=True)
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_401_failure_signals(self, mock_configuration, mock_signal, mock_oauth):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(body="You do not have permission to view this directory or page.", status=401)
            ],
        )

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        agent._login.retry.wait = wait_none()

        expected_calls = [
            call("request-fail"),
            call().send(
                agent,
                slug=agent.scheme_slug,
                channel="",
                error="STATUS_LOGIN_FAILED",
            ),
        ]

        with self.assertRaises(LoginError):
            agent.login(credentials)

        mock_signal.assert_has_calls(expected_calls)

    @mock.patch("app.agents.iceland.token_store.set")
    def test_store_token(self, mock_iceland_token_store):
        mock_iceland_token_store.return_value = True
        mock_acteol_access_token = "abcde12345fghij"
        mock_current_timestamp = 123456789
        expected_token = {
            "acteol_access_token": mock_acteol_access_token,
            "timestamp": mock_current_timestamp,
        }

        with unittest.mock.patch.object(self.wasabi.token_store, "set", return_value=True):
            token = self.wasabi._store_token(
                acteol_access_token=mock_acteol_access_token,
                current_timestamp=mock_current_timestamp,
            )

            # THEN
            assert self.wasabi.token_store.set.called_once_with(self.wasabi.scheme_id, json.dumps(expected_token))
            assert token == expected_token


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


class TestIcelandValidate(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        credentials = cred
        credentials.pop("merchant_identifier", None)

        cls.i.attempt_login(cred)

    def test_validate(self):
        balance = self.i.balance()
        self.assertIsNotNone(balance)


class TestIcelandFail(TestCase):
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
