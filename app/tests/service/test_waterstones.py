import unittest
from app.agents.exceptions import LoginError
from app.agents.waterstones import Waterstones
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestWaterstones(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = Waterstones(*AGENT_CLASS_ARGUMENTS)
        cls.w.attempt_login(CREDENTIALS['the-waterstones-card'])

    def test_login(self):
        self.assertEqual(self.w.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.w.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.w.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestWaterstonesFail(unittest.TestCase):

    def test_login_fail(self):
        w = Waterstones(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            w.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
