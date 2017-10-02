import unittest
from app.agents.exceptions import LoginError
from app.agents.enterprise import Enterprise
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestEnterprise(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = Enterprise(1, 1)
        cls.e.attempt_login(CREDENTIALS['enterprise'])

    def test_login(self):
        self.assertEqual(self.e.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.e.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)


class TestEnterpriseFail(unittest.TestCase):

    def test_login_fail(self):
        en = Enterprise(1, 1)
        credentials = {
            'username': '3213213@bad.com',
            'password': '3213213123',
        }
        with self.assertRaises(LoginError) as e:
            en.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        en = Enterprise(1, 1)
        credentials = {
            'username': 'chris.gormley2@me.com',
            'password': 'DDHansbrics101',
        }
        with self.assertRaises(LoginError) as e:
            en.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
