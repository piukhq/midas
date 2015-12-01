import unittest
from app.agents import schemas
from app.agents.nectar import Nectar
from urllib.parse import urlsplit
from app.tests.service.logins import CREDENTIALS


class TestNectar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Nectar(1, 1)
        cls.b.attempt_login(CREDENTIALS["nectar"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

        # Make sure the hashes are unique.
        hashes = [t['hash'] for t in transactions]
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
