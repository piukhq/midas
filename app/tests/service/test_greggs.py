import unittest
from app.agents.greggs import Greggs
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestGreggs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = Greggs(1, 1)
        cls.g.attempt_login(CREDENTIALS["greggs"])

    def test_login(self):
        self.assertEqual(self.g.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.g.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.g.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d/7 towards a free coffee?$')


class TestGreggsFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        credentials = CREDENTIALS["bad"]
        g = Greggs(1, 1)
        with self.assertRaises(LoginError) as e:
            g.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
