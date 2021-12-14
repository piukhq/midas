from unittest import TestCase, mock, main
from unittest.mock import ANY, MagicMock, call

import httpretty
import json

import app.agents.iceland
from app.agents.exceptions import LoginError
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.agents.iceland import Iceland
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE

cred = {
    "email": "testemail@testbink.com",
    "password": "testpassword",
}

example_response_200 = {
    "card_number": "6332040030541927281",
    "barcode": "633204003054192728100088",
    "balance": 0.0,
    "unit": "GBP",
    "alt_balance": 0.0,
    "message_uid": "cd5ba192-8445-4d3f-9eff-cec90fff4185",
    "record_uid": "pym1834v0zrqxnrmdod6jdglepko5972",
    "merchant_scheme_id1": "ygdxz4y73lko5nvj500npr1jm9082vqe",
    "merchant_scheme_id2": "46887678"
}


# Needs to be renamed to TestIceland once it has replaced the existing class TestIceland
class TestIcelandTemp(TestCase):
    @mock.patch("app.agents.iceland.Iceland._get_oauth_token", return_value="12345")
    @mock.patch("app.agents.iceland.Configuration")
    def test_login_200(self, mock_configuration, mock_oath):
        merchant_url = "https://customergateway-uat.iceland.co.uk/api/v1/bink/link"
        credentials = {"card_number": "0000000000000000000", "last_name": "Smith", "postcode": "XX0 0XX"}

        mock_configuration_object = MagicMock()
        mock_configuration_object.merchant_url = merchant_url
        mock_configuration_object.handler_type = (2, "VALIDATE")
        mock_configuration.return_value = mock_configuration_object

        httpretty.register_uri(
            method=httpretty.POST,
            uri=merchant_url,
            responses=[httpretty.Response(body=json.dumps({}), status=200)],
        )

        agent = Iceland(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card-temp")

        agent.login(credentials)


# class TestIceland(TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS, scheme_slug="iceland-bonus-card")
#         cls.i.attempt_login(cred)
#
#     def test_fetch_balance(self):
#         balance = self.i.balance()
#         self.assertIsNotNone(balance)
#
#     def test_transactions(self):
#         transactions = self.i.transactions()
#         self.assertIsNotNone(transactions)
#
#
# class TestIcelandValidate(TestCase):
#     @classmethod
#     def setUpClass(cls):
#         cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
#         credentials = cred
#         credentials.pop("merchant_identifier", None)
#
#         cls.i.attempt_login(cred)
#
#     def test_validate(self):
#         balance = self.i.balance()
#         self.assertIsNotNone(balance)
#
#
# class TestIcelandFail(TestCase):
#     def test_login_fail(self):
#         i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
#         credentials = cred
#         credentials["last_name"] = "midastest"
#         credentials.pop("merchant_identifier", None)
#         with self.assertRaises(LoginError) as e:
#             i.attempt_login(credentials)
#         self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == "__main__":
    main()
