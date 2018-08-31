import unittest
from app.agents.exceptions import LoginError
from app.agents.decathlon import Decathlon
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestDecathlon(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = Decathlon(*AGENT_CLASS_ARGUMENTS)
        cls.d.attempt_login(CREDENTIALS['decathlon-card'])

    def test_login(self):
        self.assertEqual(self.d.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.d.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ £5 vouchers?$|^$')

    def test_transactions(self):
        transactions = self.d.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestDecathlonFail(unittest.TestCase):

    def test_login_fail(self):
        d = Decathlon(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
