import unittest
from app.agents.exceptions import LoginError
from app.agents.beefeater import Beefeater
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestBeefeater(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Beefeater(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS['beefeater-grill-reward-club'])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ discount voucher[s]?$|^$')


class TestBeefeaterFail(unittest.TestCase):

    def test_login_fail(self):
        b = Beefeater(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
