import unittest
from app.agents.exceptions import LoginError
from app.agents.carlson import Carlson
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestCarlson(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Carlson(1, 1)
        cls.m.attempt_login(CREDENTIALS['clubcarlson'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^(?:Premium|Standard) award night, category [1-7]$|^$')


class TestCarlsonFail(unittest.TestCase):

    def test_login_fail(self):
        m = Carlson(1, 1)
        credentials = {
            'username': '0000000000000000',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
