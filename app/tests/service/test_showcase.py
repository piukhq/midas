import unittest
from app.agents.exceptions import LoginError
from app.agents.showcase import Showcase
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestShowcase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Showcase(1, 1)
        cls.m.attempt_login(CREDENTIALS['showcase'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestShowcaseFail(unittest.TestCase):

    def test_login_fail(self):
        m = Showcase(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
