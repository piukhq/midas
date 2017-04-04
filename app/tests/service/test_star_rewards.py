import unittest
from app.agents.exceptions import LoginError
from app.agents.star_rewards import StarRewards
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestStarRewards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = StarRewards(1, 1)
        cls.s.attempt_login(CREDENTIALS['star_rewards'])

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
        s = StarRewards(1, 1)
        with self.assertRaises(LoginError) as e:
            s.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
