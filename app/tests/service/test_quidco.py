import unittest
from app.agents.exceptions import LoginError
from app.agents.quidco import Quidco
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestQuidco(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = Quidco(1, 1)
        cls.q.attempt_login(CREDENTIALS['quidco'])

    def test_login(self):
        self.assertEqual(self.q.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.q.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.q.balance()
        schemas.balance(balance)


class TestQuidcoFail(unittest.TestCase):
    def test_login_fail(self):
        q = Quidco(1, 1)
        with self.assertRaises(LoginError) as e:
            q.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
