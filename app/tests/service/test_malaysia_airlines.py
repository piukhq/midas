import unittest
from app.agents.exceptions import LoginError
from app.agents.malaysia_airlines import MalaysiaAirlines
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestMalaysiaAirlines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = MalaysiaAirlines(1, 1)
        cls.m.attempt_login(CREDENTIALS['malaysia_airlines'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestMalaysiaAirlinesFail(unittest.TestCase):
    def test_login_fail(self):
        m = MalaysiaAirlines(1, 1)
        credentials = {
            'card_number': 'MH000000000',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
