import unittest
from app.agents.exceptions import LoginError
from app.agents.lufthansa import Lufthansa
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestLufthansa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Lufthansa(1, 1)
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
    def test_login_bad_pin(self):
        m = Lufthansa(1, 1)
        credentials = {
            'card_number': '992000656640646',
            'pin': '552960',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_card_number(self):
        m = Lufthansa(1, 1)
        credentials = {
            'card_number': '9920006566406460',
            'pin': '55296',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
