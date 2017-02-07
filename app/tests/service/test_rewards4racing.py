import unittest
from app.agents.exceptions import LoginError
from app.agents.rewards4racing import Rewards4Racing
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestRewards4Racing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = Rewards4Racing(1, 1)
        cls.r.attempt_login(CREDENTIALS['rewards4racing'])

    def test_login(self):
        self.assertEqual(self.r.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.r.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.r.balance()
        schemas.balance(balance)


class TestRewards4RacingFail(unittest.TestCase):

    def test_login_fail(self):
        r = Rewards4Racing(1, 1)
        with self.assertRaises(LoginError) as e:
            r.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
