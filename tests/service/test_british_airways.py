import unittest
from urllib.parse import urlsplit
from app.agents import schemas
from app.agents.british_airways import BritishAirways
from tests.service.logins import CREDENTIALS


class TestBritishAirways(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = BritishAirways(1, 1)
        cls.b.attempt_login(CREDENTIALS["british-airways"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/travel/viewaccount/execclub/_gf/en_gb')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
