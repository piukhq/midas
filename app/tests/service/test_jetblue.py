import unittest
from app.agents.exceptions import LoginError
from app.agents.jetblue import JetBlue
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestJetBlue(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.j = JetBlue(*AGENT_CLASS_ARGUMENTS)
        cls.j.attempt_login(CREDENTIALS['trueblue'])

    def test_login(self):
        self.assertTrue(self.j.is_successful_login)

    def test_transactions(self):
        transactions = self.j.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.j.balance()
        schemas.balance(balance)


class TestJetBlueFail(unittest.TestCase):

    def test_login_fail(self):
        j = JetBlue(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            j.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
