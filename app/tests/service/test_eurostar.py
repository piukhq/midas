import unittest
from app.agents.exceptions import LoginError
from app.agents.eurostar import Eurostar
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestEurostar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = Eurostar(1, 1)
        cls.e.attempt_login(CREDENTIALS['eurostar-plus-points'])

    def test_login(self):
        self.assertEqual(self.e.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ £20 e-voucher[s]?$|^$')


class TestEurostarFail(unittest.TestCase):

    def test_login_fail(self):
        eu = Eurostar(1, 1)
        with self.assertRaises(LoginError) as e:
            eu.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        eu = Eurostar(1, 1)
        credentials = {
            'email': 'chris.gormley2@me.com',
            'password': 'QDHansbrics81',
        }
        with self.assertRaises(LoginError) as e:
            eu.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
