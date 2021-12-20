import json
from decimal import Decimal
from unittest import TestCase, main, mock
from unittest.mock import MagicMock

import httpretty

from app.agents.base import Balance
from app.agents.exceptions import LoginError, AgentError
from app.agents.iceland import Iceland
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.scheme_account import TWO_PLACES
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE

cred = {
    "email": "testemail@testbink.com",
    "password": "testpassword",
}


# Needs to be renamed to TestIceland once it has replaced the existing class TestIceland
class TestIcelandTemp(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.credentials = {"card_number": "0000000000000000000", "last_name": "Smith", "postcode": "XX0 0XX"}

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

        self.assertEqual(agent._get_oauth_token(), "a_token")

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

        AGENT_CLASS_ARGUMENTS_FOR_VALIDATE[1]["credentials"] = self.credentials
        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")

        agent.login(self.credentials)
        self.assertEqual(agent.headers, {"Authorization": f"Bearer {'a_token'}"})
        self.assertIn("barcode", str(agent.user_info))
        self.assertEqual(agent._balance_amount, 10.0)

    @httpretty.activate
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="a_token")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200_validation_error_401(self, mock_configuration, mock_oath):
        mock_configuration.return_value = self.mock_link_configuration_object()
        httpretty.register_uri(
            method=httpretty.POST,
            uri=self.merchant_url,
            responses=[
                httpretty.Response(
                    body=json.dumps({"error_codes": [{"code": "VALIDATION", "description": "card_number not valid."}]}),
                    status=200,
                )
            ],
        )

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        with self.assertRaises(LoginError) as e:
            agent.login(self.credentials)
        self.assertEqual(e.exception.code, 401)

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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        with self.assertRaises(LoginError) as e:
            agent.login(self.credentials)
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        with self.assertRaises(LoginError) as e:
            agent.login(self.credentials)
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
                        {"error_codes": [{"code": "CARD_NOT_REGISTERED", "description": "Card has not been registered"}]}
                    ),
                    status=200,
                )
            ],
        )

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        with self.assertRaises(LoginError) as e:
            agent.login(self.credentials)
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

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        with self.assertRaises(LoginError) as e:
            agent.login(self.credentials)
        self.assertEqual(e.exception.code, 439)

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


class TestIceland(TestCase):
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
