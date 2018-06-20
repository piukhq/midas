import unittest
from app.agents.exceptions import LoginError
from app.agents.starwood import Starwood
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestStarwood(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = Starwood(*AGENT_CLASS_ARGUMENTS)
        cls.m.attempt_login(CREDENTIALS['starwood-preferred-guest'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '(^$)|(^\$\d+ amazon gift card$)')


class TestStarwoodFail(unittest.TestCase):

    def test_login_fail(self):
        m = Starwood(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '321321321',
            'password': '321321321',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_mfa(self):
        m = Starwood(*AGENT_CLASS_ARGUMENTS)
        credentials = CREDENTIALS['starwood-preferred-guest'].copy()
        credentials['favourite_place'] = 'totally incorrect'
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid mfa')


if __name__ == '__main__':
    unittest.main()
