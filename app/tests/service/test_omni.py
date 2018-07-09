import unittest
from app.agents.exceptions import LoginError
from app.agents.omni import Omni
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestOmni(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Omni(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['omni'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^(?:Black|Platinum|Gold) membership$')


class TestOmniFail(unittest.TestCase):

    def test_login_fail(self):
        m = Omni(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
