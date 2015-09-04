import unittest

from app.agents.cooperative import Cooperative
from app.agents import schemas
from app.agents.exceptions import LoginError
from tests.service.logins import CREDENTIALS


class TestCooperative(unittest.TestCase):
    def setUp(self):
        self.b = Cooperative(retry_count=1)
        self.b.attempt_login(CREDENTIALS["cooperative"])

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
        credentials['card_number'] = '633174911212875980'
        b = Cooperative(retry_count=1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")

    def test_login_bad_mfa(self):
        credentials = CREDENTIALS["cooperative"]
        credentials['place_of_birth'] = 'auckland'
        b = Cooperative(retry_count=1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "INVALID_MFA_INFO")

if __name__ == '__main__':
    unittest.main()
