import unittest
from app.agents import schemas
from app.agents.nectar import Nectar
from tests.service.logins import CREDENTIALS


class TestNectar(unittest.TestCase):
    def setUp(self):
        self.b = Nectar(retry_count=1)
        self.b.attempt_login(CREDENTIALS["nector"])

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
