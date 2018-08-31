import unittest
from app.agents.exceptions import LoginError
from app.agents.odeon import Odeon
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestOdeon(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = Odeon(*AGENT_CLASS_ARGUMENTS)
        cls.o.attempt_login(CREDENTIALS['odeon'])

    def test_login(self):
        self.assertEqual(self.o.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.o.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.o.balance()
        schemas.balance(balance)


class TestOdeonFail(unittest.TestCase):

    def test_login_fail(self):
        o = Odeon(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            o.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
