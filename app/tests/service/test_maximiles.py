import unittest
from app.agents.exceptions import LoginError
from app.agents.maximiles import Maximiles
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestMaximiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Maximiles(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['maximiles'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestMaximilesFail(unittest.TestCase):

    def test_login_fail(self):
        m = Maximiles(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
