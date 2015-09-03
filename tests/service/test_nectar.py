import unittest
from app.agents import schemas
from app.agents.nectar import Nectar
from urllib.parse import urlsplit


class TestNectar(unittest.TestCase):
    def setUp(self):
        credentials = {
            'card_prefix': '98263000',
            'card_number': '30842203013',
            'password': 'QMHansbrics6',
        }
        self.b = Nectar(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/')

    # def test_transactions(self):
    #     transactions = self.b.transactions()
    #     schemas.transactions(transactions)
    #
    # def test_balance(self):
    #     balance = self.b.balance()
    #     schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
