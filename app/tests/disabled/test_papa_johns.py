import unittest
from app.agents.exceptions import LoginError
from app.agents.papa_johns import PapaJohns
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestPapaJohns(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = PapaJohns(1, 1)
        cls.b.attempt_login(CREDENTIALS['papa_johns'])

    def test_login(self):
        self.assertTrue(self.b.is_login_successful)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestPapaJohnsFail(unittest.TestCase):

    def test_login_fail(self):
        b = PapaJohns(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
