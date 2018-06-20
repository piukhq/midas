import unittest
from app.agents.exceptions import LoginError
from app.agents.rewards4golf import Rewards4Golf
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestRewards4Golf(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = Rewards4Golf(*AGENT_CLASS_ARGUMENTS)
        cls.r.attempt_login(CREDENTIALS['rewards4golf'])

    def test_login(self):
        self.assertEqual(self.r.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.r.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.r.balance()
        schemas.balance(balance)


class TestRewards4GolfFail(unittest.TestCase):

    def test_login_fail(self):
        r = Rewards4Golf(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            r.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
