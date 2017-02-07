import unittest
from app.agents.exceptions import LoginError
from app.agents.foyles_bookstore import FoylesBookstore
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestFoylesBookstore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = FoylesBookstore(1, 1)
        cls.w.attempt_login(CREDENTIALS['foyalty'])

    def test_login(self):
        self.assertEqual(self.w.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.w.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.w.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestFoylesBookstoreFail(unittest.TestCase):

    def test_login_fail(self):
        w = FoylesBookstore(1, 1)
        credentials = {
            'barcode': '000000000000',
            'email': 'bad@bad.com',
        }
        with self.assertRaises(LoginError) as e:
            w.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
