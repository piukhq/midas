import unittest
from app.agents.exceptions import LoginError
from app.agents.qantas import Qantas
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestQantas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Qantas(1, 1, False)
        cls.m.attempt_login(CREDENTIALS['qantas'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestQantasFail(unittest.TestCase):
    def test_login_fail(self):
        m = Qantas(1, 1, False)
        credentials = {
            "member_number": "9999999999",
            "last_name": "bad",
            "pin": "9999",
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
