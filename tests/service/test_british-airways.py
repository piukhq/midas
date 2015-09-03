import unittest
from urllib.parse import urlsplit
from app.agents import schemas
from app.agents.british_airways import BritishAirways


class TestBritishAirways(unittest.TestCase):
    def setUp(self):
        credentials = {
            'card_number': 38198503,
            'password': 'Buster69'
        }
        self.b = BritishAirways(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        #self.assertEqual(urlsplit(self.b.browser.url).path, '/webapp/wcs/stores/servlet/ADCAccountSummary')

    def test_transactions(self):
        transactions = self.b.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
