import unittest
from app.agents.exceptions import LoginError
from app.agents.monsoon import Monsoon
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestMonsoon(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Monsoon(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['monsoon'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful())

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d+\.\d\d$')


class TestMonsoonFail(unittest.TestCase):

    def test_login_fail(self):
        m = Monsoon(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
