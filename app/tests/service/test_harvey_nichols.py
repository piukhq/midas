import unittest
from app.agents.harvey_nichols import HarveyNichols
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestHarveyNichols(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = HarveyNichols(1, 1)
        cls.h.attempt_login(CREDENTIALS['harvey_nichols'])

    def test_login(self):
        pass

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)


class TestHarveyNicholsFail(unittest.TestCase):

    def test_login_fail(self):
        pass


if __name__ == '__main__':
    unittest.main()
