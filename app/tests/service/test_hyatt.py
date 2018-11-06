import unittest
from app.agents.exceptions import LoginError
from app.agents.hyatt import Hyatt
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestHyatt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Hyatt(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['gold-passport'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestHyattFail(unittest.TestCase):

    def test_login_fail(self):
        m = Hyatt(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '000000000F',
            'last_name': 'wrong',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
