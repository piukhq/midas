import unittest
from app.agents.exceptions import LoginError
from app.agents.holland_and_barrett import HollandAndBarrett
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestHollandAndBarrett(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = HollandAndBarrett(1, 1)
        cls.m.attempt_login(CREDENTIALS['rewards-for-life'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestHollandAndBarrettFail(unittest.TestCase):

    def test_login_fail(self):
        m = HollandAndBarrett(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
