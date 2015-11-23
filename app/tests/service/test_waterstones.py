import unittest
from app.agents.exceptions import LoginError
from app.agents.waterstones import Waterstones
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestWaterstones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = Waterstones(1, 1)
        cls.w.attempt_login(CREDENTIALS['waterstones'])

    def test_login(self):
        self.assertEqual(self.w.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.w.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.w.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)


class TestWaterstonesFail(unittest.TestCase):
    def test_login_fail(self):
        w = Waterstones(1, 1)
        with self.assertRaises(LoginError) as e:
            w.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
