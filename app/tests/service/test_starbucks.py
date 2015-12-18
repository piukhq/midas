import unittest
from app.agents.exceptions import LoginError
from app.agents.starbucks import Starbucks
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestStarbucks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Starbucks(1, 1)
        cls.s.attempt_login(CREDENTIALS['starbucks'])

    def test_balance(self):
        balance = self.s.balance()
        schemas.balance(balance)
        self.assertTrue(balance['points'] >= 0 and balance['points'] <= 15)
        self.assertRegex(balance['value_label'], '^\d+/15 coffees$')

if __name__ == '__main__':
    unittest.main()
