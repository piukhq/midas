import unittest
from app.agents.exceptions import LoginError
from app.agents.papa_johns import PapaJohns
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestPapaJohns(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = PapaJohns(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS['papa-johns'])

    def test_login(self):
        self.assertTrue(self.b.is_login_successful)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestPapaJohnsFail(unittest.TestCase):

    def test_login_fail(self):
        b = PapaJohns(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
