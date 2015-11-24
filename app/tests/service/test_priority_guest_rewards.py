import unittest
from app.agents.exceptions import LoginError
from app.agents.priority_guest_rewards import PriorityGuestRewards
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestPriorityGuestRewards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = PriorityGuestRewards(1, 1)
        cls.m.attempt_login(CREDENTIALS['priority-guest-rewards'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestPriorityGuestRewardsFail(unittest.TestCase):
    def test_login_fail(self):
        m = PriorityGuestRewards(1, 1)
        credentials = {
            'username': 'R0000000',
            'password': '32132132',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
