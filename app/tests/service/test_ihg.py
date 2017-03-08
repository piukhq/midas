import unittest
from app.agents.exceptions import LoginError
from app.agents.ihg import Ihg
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestIhg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Ihg(1, 1)
        cls.m.attempt_login(CREDENTIALS['ihg'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestIHGFail(unittest.TestCase):
    def test_login_fail(self):
        m = Ihg(1, 1)
        credentials = {
            'username': 'bad@bad.com',
            'pin': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_pin(self):
        m = Ihg(1, 1)
        credentials = {
            'username': 'la@loyaltyangels.com',
            'pin': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_long_pin(self):
        m = Ihg(1, 1)
        credentials = {
            'username': 'la@loyaltyangels.com',
            'pin': '12900'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
