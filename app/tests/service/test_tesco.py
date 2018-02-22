import unittest
from app.agents.tesco import Tesco
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError


class TestTesco(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Tesco(1, 1)
        credentials = CREDENTIALS.get("tesco-clubcard") or CREDENTIALS.get("tesco-clubcard1")
        cls.b.attempt_login(credentials)

    def test_login(self):
        self.assertTrue(self.b.is_login_successful)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestTescoFail(unittest.TestCase):

    def test_login_fail(self):
        b = Tesco(1, 1)
        credentials = {
            'card_number': '979999999999999',
            'email': 'magnanimiter@crucem.sustine',
            'password': 'noblesseoblige',
        }
        with self.assertRaises(LoginError) as e:
            b.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
