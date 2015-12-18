import unittest

from app.agents.cooperative import Cooperative
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestCooperative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Cooperative(1, 1)
        cls.b.attempt_login(CREDENTIALS["cooperative"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestCooperativeFail(unittest.TestCase):
    def test_login_bad_number(self):
        credentials = CREDENTIALS["cooperative"]
        credentials['barcode'] = '633174911212875980'
        b = Cooperative(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")

    def test_login_bad_mfa(self):
        credentials = CREDENTIALS["cooperative"]
        credentials['place_of_birth'] = 'auckland'
        b = Cooperative(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")

if __name__ == '__main__':
    unittest.main()
