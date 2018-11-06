import unittest
from app.agents.exceptions import LoginError
from app.agents.handm import HAndM
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestHAndM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = HAndM(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['handm-club'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestHAndMFail(unittest.TestCase):
    def test_login_bad_email(self):
        m = HAndM(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'email': 'bad@bad.com',
            'password': 'Loyalty01'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = HAndM(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'email': ' loyaltycards01@gmail.com',
            'password': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
