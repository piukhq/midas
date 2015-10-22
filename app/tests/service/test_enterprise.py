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

    def test_balance_after_transactions(self):
        self.e.transactions()
        balance = self.e.balance()
        schemas.balance(balance)

class TestEnterpriseFail(unittest.TestCase):
    def test_login_fail(self):
        en = Enterprise(1, 1)
        with self.assertRaises(LoginError) as e:
            en.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
