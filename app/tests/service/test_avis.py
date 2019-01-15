import unittest
from app.agents.avis import Avis
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestAvis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Avis(*AGENT_CLASS_ARGUMENTS)
        cls.d.attempt_login(CREDENTIALS['avis'])

    def test_login(self):
        self.assertEqual(self.d.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.d.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.d.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], r'^€\d*\.\d\d$')


class TestAvisFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        d = Avis(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
