import unittest
from app.agents.exceptions import LoginError
from app.agents.eurostar import Eurostar
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestEurostar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = Eurostar(1, 1)
        cls.e.attempt_login(CREDENTIALS['eurostar'])

    def test_login(self):
        self.assertTrue(self.e.is_login_successful)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ £20 e-voucher[s]?$|^$')

    def test_transactions(self):
        transactions = self.e.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestEurostarFail(unittest.TestCase):

    def test_login_fail(self):
        eu = Eurostar(1, 1)
        with self.assertRaises(LoginError) as e:
            eu.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
