import unittest
from app.agents.harvey_nichols import HarveyNichols
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestHarveyNichols(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = HarveyNichols(1, 1)
        cls.h.attempt_login(CREDENTIALS['harvey-nichols'])

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)

    def test_register(self):
        result = self.h.register(CREDENTIALS['harvey-nichols'])
        self.assertEqual(result, {'message': 'success'})


if __name__ == '__main__':
    unittest.main()
