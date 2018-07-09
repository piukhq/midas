import unittest
from app.agents.exceptions import LoginError
from app.agents.enterprise import Enterprise
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestEnterprise(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.e = Enterprise(*AGENT_CLASS_ARGUMENTS)
        cls.e.attempt_login(CREDENTIALS['enterprise'])

    def test_login(self):
        self.assertEqual(self.e.response.status_code, 200)

    def test_transactions(self):
        transactions = self.e.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.e.balance()
        schemas.balance(balance)


class TestEnterpriseFail(unittest.TestCase):

    def test_login_fail(self):
        en = Enterprise(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': '3213213@bad.com',
            'password': '3213213123',
        }
        with self.assertRaises(LoginError) as e:
            en.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

    def test_login_bad_password(self):
        en = Enterprise(*AGENT_CLASS_ARGUMENTS)
        credentials = {
            'username': 'chris.gormley2@me.com',
            'password': 'DDHansbrics101',
        }
        with self.assertRaises(LoginError) as e:
            en.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
