import unittest
from app.agents.exceptions import LoginError
from app.agents.tabletable import Tabletable
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestTabletable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Tabletable(1, 1)
        cls.t.attempt_login(CREDENTIALS['tabletable'])

    def test_login(self):
        self.assertEqual(self.t.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.t.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.t.balance()
        schemas.balance(balance)


class TestTabletableFail(unittest.TestCase):
    def test_login_fail(self):
        t = Tabletable(1, 1)
        with self.assertRaises(LoginError) as e:
            t.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
