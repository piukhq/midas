import unittest
from app.agents.exceptions import LoginError
from app.agents.heathrow import Heathrow
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestHeathrow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = Heathrow(*AGENT_CLASS_ARGUMENTS)
        cls.h.attempt_login(CREDENTIALS['heathrow-rewards'])

    def test_login(self):
        self.assertEqual(self.h.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], r'^\d+ £5 vouchers?$|^$')


class TestHeathrowFail(unittest.TestCase):

    def test_login_fail(self):
        h = Heathrow(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            h.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
