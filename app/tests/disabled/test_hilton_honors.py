import unittest

from app.agents.hilton_honors import Hilton
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestHilton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.miner = Hilton(retry_count=1, scheme_id=1)
        cls.miner.attempt_login(CREDENTIALS["hilton-honors"])

    def test_transactions(self):
        transactions = self.miner.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.miner.balance()
        schemas.balance(balance)


class TestHiltonFail(unittest.TestCase):
    def test_failed_login(self):
        miner = Hilton(1, 1)
        credentials = {
            'username': '999999999',
            'password': 'bad'
        }
        with self.assertRaises(LoginError) as e:
            miner.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
