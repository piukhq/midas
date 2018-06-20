import unittest
from app.agents.toysrus import Toysrus
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestToysrus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Toysrus(*AGENT_CLASS_ARGUMENTS)
        cls.t.attempt_login(CREDENTIALS["toysrus"])

    def test_login(self):
        self.assertEqual(self.t.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.t.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.t.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestToysrusFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        credentials = CREDENTIALS["bad"]
        t = Toysrus(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            t.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
