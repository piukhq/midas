import unittest
from app.agents.exceptions import LoginError
from app.agents.lufthansa import Lufthansa
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestLufthansa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Lufthansa(1, 1, False)
        cls.m.attempt_login(CREDENTIALS['lufthansa'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestLufthansaFail(unittest.TestCase):
    def test_login_fail(self):
        m = Lufthansa(1, 1, False)
        credentials = {
            'card_number': '999999999999999',
            'pin': '99999',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
