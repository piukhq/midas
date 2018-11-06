import unittest
from app.agents.avios import Avios
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS
from app.agents import schemas


class TestAvios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Avios(*AGENT_CLASS_ARGUMENTS)
        cls.b.attempt_login(CREDENTIALS["avios"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertEqual('', balance['value_label'])


class TestAviosFail(unittest.TestCase):
    def test_login_bad_number(self):
        credentials = CREDENTIALS["bad"]
        b = Avios(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")
