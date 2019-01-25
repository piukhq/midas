import unittest
from app.agents.exceptions import LoginError
from app.agents.malaysia_airlines import MalaysiaAirlines
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestMalaysiaAirlines(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = MalaysiaAirlines(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['enrich'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestMalaysiaAirlinesFail(unittest.TestCase):

    def test_login_fail(self):
        m = MalaysiaAirlines(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': 'MH000000000',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
