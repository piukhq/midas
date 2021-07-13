import unittest
from app.agents.exceptions import LoginError
from app.agents.merchant_api_generic import MerchantAPIGeneric
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS, AGENT_CLASS_ARGUMENTS_FOR_VALIDATE


class TestIceland(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS, scheme_slug="iceland-bonus-card")
        cls.i.attempt_login(CREDENTIALS["iceland-bonus-card"])

    def test_fetch_balance(self):
        balance = self.i.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.i.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestIcelandValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        credentials = CREDENTIALS["iceland-bonus-card"]
        credentials.pop("merchant_identifier", None)

        cls.i.attempt_login(CREDENTIALS["iceland-bonus-card"])

    def test_validate(self):
        balance = self.i.balance()
        schemas.balance(balance)


class TestIcelandFail(unittest.TestCase):
    def test_login_fail(self):
        i = MerchantAPIGeneric(*AGENT_CLASS_ARGUMENTS_FOR_VALIDATE, scheme_slug="iceland-bonus-card")
        credentials = CREDENTIALS["iceland-bonus-card"]
        credentials["last_name"] = "midastest"
        credentials.pop("merchant_identifier", None)
        with self.assertRaises(LoginError) as e:
            i.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == "__main__":
    unittest.main()
