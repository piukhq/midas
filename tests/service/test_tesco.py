import unittest
from app.agents.tesco import Tesco
from urllib.parse import urlsplit
from app.agents import schemas


class TestTesco(unittest.TestCase):
    def setUp(self):
        credentials = {
            'user_name': 'julie.gormley100@gmail.com',
            'password': 'NSHansbrics5',
            'card_number': '634004024051328070',
        }
        self.b = Tesco(credentials, 1)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/Clubcard/MyAccount/Home.aspx')

    def test_transactions(self):
        transactions = self.b.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
