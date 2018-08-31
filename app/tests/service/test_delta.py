import unittest
from app.agents.exceptions import LoginError
from app.agents.delta import Delta
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestDelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Delta(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['delta-skymiles'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestDeltaFail(unittest.TestCase):
    def test_login_bad_username(self):
        m = Delta(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '321321321',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        m = Delta(*AGENT_CLASS_ARGUMENTS)
        credentials = CREDENTIALS['delta-skymiles'].copy()
        credentials['password'] = '32132132'

        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
