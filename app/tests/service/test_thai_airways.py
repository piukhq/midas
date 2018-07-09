import unittest
from app.agents.exceptions import LoginError
from app.agents.thai_airways import ThaiAirways
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestThaiAirways(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = ThaiAirways(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['royal-orchid-plus'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful())

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestThaiAirwaysFail(unittest.TestCase):

    def test_login_bad_username(self):
        m = ThaiAirways(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '321321321',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = ThaiAirways(*AGENT_CLASS_ARGUMENTS)
        credentials = CREDENTIALS['royal-orchid-plus'].copy()
        credentials['password'] = '32132132'

        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
