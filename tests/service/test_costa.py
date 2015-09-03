import unittest
from app.agents.costa import Costa
from app.agents import schemas
from app.agents.exceptions import LoginError
from tests.service.logins import CREDENTIALS


class TestCosta(unittest.TestCase):
    def setUp(self):
        self.b = Costa(retry_count=1)
        self.b.attempt_login(CREDENTIALS["costa"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

    def test_login_fail(self):
        b = Costa(retry_count=1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")

if __name__ == '__main__':
    unittest.main()
