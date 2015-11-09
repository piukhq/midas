import unittest
from app.agents.morrisons import Morrisons
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestMorrisons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Morrisons(1, 1)
        cls.b.attempt_login(CREDENTIALS["morrisons"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)


class TestMorrisonsFail(unittest.TestCase):
    def test_login_fail(self):
        b = Morrisons(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "Invalid credentials")

if __name__ == '__main__':
    unittest.main()
