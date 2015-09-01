import unittest
from app.agents.boots import Boots
from urllib.parse import urlsplit
from app.agents import schemas


class TestBoots(unittest.TestCase):
    def setUp(self):
        credentials = {
            'user_name': 'julie.gormley100@gmail.com',
            'password': 'RAHansbrics5'
        }
        self.b = Boots(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/webapp/wcs/stores/servlet/ADCAccountSummary')

    def test_transactions(self):
        transactions = self.b.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
