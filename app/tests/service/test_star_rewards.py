import unittest
from app.agents.exceptions import LoginError
from app.agents.star_rewards import StarRewards
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestStarRewards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = StarRewards(*AGENT_CLASS_ARGUMENTS)
        cls.s.attempt_login(CREDENTIALS['star-rewards'])

    def test_login(self):
        self.assertEqual(self.s.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.s.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.s.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestStarRewardsFail(unittest.TestCase):

    def test_login_fail(self):
        s = StarRewards(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            "card_number": "7000000000000000001",
            'password': '234234',
        }
        with self.assertRaises(LoginError) as e:
            s.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
