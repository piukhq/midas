import unittest

from app.agents.marriott import Marriott
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestMarriott(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Marriott(1, 1)
        cls.b.attempt_login(CREDENTIALS["marriott"])

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestMarriottFail(unittest.TestCase):
    def test_failed_login(self):
        b = Marriott(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()