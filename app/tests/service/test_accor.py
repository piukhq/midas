import unittest
from app.agents.exceptions import LoginError
from app.agents.accor import Accor
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestAccor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Accor(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['le-club'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^€40 discount on your next stay$|^$')


class TestAccorFail(unittest.TestCase):

    def test_login_fail(self):
        m = Accor(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '3213123123123',
            'password': '3213231312312',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
