import unittest
from app.agents import schemas
from app.agents.avios import Avios
from tests.service.logins import CREDENTIALS


class TestAvios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Avios(1, 1)
        cls.b.attempt_login(CREDENTIALS["avios"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    # def test_balance(self):
    #     balance = self.b.balance()
    #     schemas.balance(balance)
    #
    # def test_transactions(self):
    #     transactions = self.b.transactions()
    #     self.assertTrue(transactions)
    #     schemas.transactions(transactions)