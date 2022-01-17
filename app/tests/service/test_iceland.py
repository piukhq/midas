from unittest import TestCase, main

from app.agents.exceptions import LoginError
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE

cred = {
    "email": "testemail@testbink.com",
    "password": "testpassword",
}


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
