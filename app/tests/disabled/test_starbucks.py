import unittest
from app.agents.exceptions import LoginError
from app.agents.starbucks import Starbucks
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestStarbucks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.s = Starbucks(*AGENT_CLASS_ARGUMENTS)
        cls.s.attempt_login(CREDENTIALS['starbucks'])

    def test_balance(self):
        balance = self.s.balance()
        schemas.balance(balance)
        self.assertTrue(balance['points'] >= 0 and balance['points'] <= 15)
        self.assertRegex(balance['value_label'], r'^\d+/15 coffees$')


class TestStarbucksFail(unittest.TestCase):

    def test_login_fail(self):
        s = Starbucks(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': 'bad@bad.com',
            'password': '321321321321',
        }
        with self.assertRaises(LoginError) as e:
            s.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
