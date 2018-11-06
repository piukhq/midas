import unittest
from app.agents.exceptions import LoginError
from app.agents.virgin import Virgin
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestVirgin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Virgin(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['virgin-flyingclub'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestVirginFail(unittest.TestCase):

    def test_login_fail(self):
        m = Virgin(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '1000000000',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
