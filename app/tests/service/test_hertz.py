import unittest
from app.agents.exceptions import LoginError
from app.agents.hertz import Hertz
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestHertz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = Hertz(1, 1)
        cls.h.attempt_login(CREDENTIALS['hertz'])

    def test_login(self):
        self.assertEqual(self.h.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ reward rental day[s]?$')


class TestHertzFail(unittest.TestCase):
    def test_login_fail(self):
        h = Hertz(1, 1)
        with self.assertRaises(LoginError) as e:
            h.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
