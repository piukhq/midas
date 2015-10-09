import unittest
from app.agents.exceptions import LoginError
from app.agents.shell import Shell
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Shell(1, 1)
        cls.b.attempt_login(CREDENTIALS["shell"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestShellFail(unittest.TestCase):
    def test_login_fail(self):
        b = Shell(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")

if __name__ == '__main__':
    unittest.main()
