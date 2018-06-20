import unittest
from app.agents.exceptions import LoginError
from app.agents.iceland import Iceland
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestIceland(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Iceland(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['iceland-bonus-card'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestIcelandFail(unittest.TestCase):
    def test_login_bad_card_number(self):
        m = Iceland(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '00000000000',
            'password': 't7Ixmj424Q'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = Iceland(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'card_number': '30403486285',
            'password': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
