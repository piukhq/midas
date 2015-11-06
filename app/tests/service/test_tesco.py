import unittest
from app.agents.tesco import Tesco
from urllib.parse import urlsplit
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError


class TestTesco(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Tesco(1, 1)
        cls.b.attempt_login(CREDENTIALS["tesco-clubcard"])

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


class TestTescoFail(unittest.TestCase):
    def test_login_fail(self):
        b = Tesco(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "Invalid credentials")

    def test_login_mfa_fail(self):
        b = Tesco(1, 1)
        credentials = CREDENTIALS["tesco-clubcard"]
        credentials['barcode'] = '634004024855326070'
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid mfa")


if __name__ == '__main__':
    unittest.main()
