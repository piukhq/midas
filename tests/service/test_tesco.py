import unittest
from app.agents.tesco import Tesco
from urllib.parse import urlsplit
from app.agents import schemas
from tests.service.logins import CREDENTIALS


class TestTesco(unittest.TestCase):
    def setUp(self):
        self.b = Tesco(retry_count=1)
        self.b.attempt_login(CREDENTIALS["tesco"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/Clubcard/MyAccount/Home.aspx')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
