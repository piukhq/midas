import unittest
from app.agents.nectar import Nectar
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestNectar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Nectar(1, 1)
        cls.b.attempt_login(CREDENTIALS["nectar"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestNectarFail(unittest.TestCase):

    def test_login_fail(self):
        b = Nectar(1, 1)
        credentials = {
            'card_number': '11111111111111',
            'password': '32132132131',
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
