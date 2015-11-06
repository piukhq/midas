import unittest
from app.agents.exceptions import LoginError
from app.agents.monsoon import Monsoon
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestMonsoon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Monsoon(1, 1)
        cls.m.attempt_login(CREDENTIALS['monsoon'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d+\.\d\d$')


class TestMonsoonFail(unittest.TestCase):
    def test_login_fail(self):
        m = Monsoon(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
