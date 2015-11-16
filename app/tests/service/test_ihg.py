import unittest
from app.agents.exceptions import LoginError
from app.agents.ihg import IHG
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestIHG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = IHG(1, 1)
        cls.m.attempt_login(CREDENTIALS['ihg'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestIHGFail(unittest.TestCase):
    def test_login_fail(self):
        m = IHG(1, 1)
        credentials = {
            'email': 'bad@bad.com',
            'pin': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
