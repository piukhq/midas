import unittest

from app.agents import schemas
from app.agents.ecrebo import Ecrebo
from app.agents.exceptions import LoginError
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS, CREDENTIALS


class TestEcrebo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = Ecrebo(*AGENT_CLASS_ARGUMENTS)
        cls.g.register(CREDENTIALS["ecrebo"])

    def test_login(self):
        self.assertIsNotNone(self.g.identifier)

    def test_transactions(self):
        transactions = self.g.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.g.balance()
        schemas.balance(balance)
        self.assertRegex(balance["value_label"], r"^\d+ points$")


class TestEcreboFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        credentials = {"card_number": "asdfghjkl"}
        g = Ecrebo(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            g.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == "__main__":
    unittest.main()
