import unittest
from app.agents.boots import Boots
from urllib.parse import urlsplit
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestBoots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Boots(1, 1)
        cls.b.attempt_login(CREDENTIALS["advantage-card"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertEqual(urlsplit(self.b.browser.url).path, '/webapp/wcs/stores/servlet/ADCAccountSummary')

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestBootsFail(unittest.TestCase):
    def test_login_bad_number(self):
        credentials = CREDENTIALS["bad"]
        b = Boots(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")


if __name__ == '__main__':
    unittest.main()
