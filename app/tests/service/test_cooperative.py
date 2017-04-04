import unittest

from app.agents.cooperative import Cooperative
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestCooperative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Cooperative(1, 1)
        cls.b.attempt_login(CREDENTIALS["cooperative"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestCooperativeFail(unittest.TestCase):
    def test_failed_login(self):
        credentials = {}
        credentials['email'] = 'chris.gormley2@me.com.com'
        credentials['password'] = 'test'
        b = Cooperative(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
