import unittest
from app.agents.exceptions import LoginError
from app.agents.rewards4fishing import Rewards4Fishing
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestRewards4Fishing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Rewards4Fishing(1, 1)
        cls.r.attempt_login(CREDENTIALS['rewards4fishing'])

    def test_login(self):
        self.assertEqual(self.r.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.r.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.r.balance()
        schemas.balance(balance)


class TestRewards4FishingFail(unittest.TestCase):
    def test_login_fail(self):
        r = Rewards4Fishing(1, 1)
        with self.assertRaises(LoginError) as e:
            r.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
