import unittest
from app.agents.exceptions import LoginError
from app.agents.aerclub import AerClub
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestAerClub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = AerClub(1, 1)
        cls.m.attempt_login(CREDENTIALS['aerclub'])

    def test_login(self):
        self.assertTrue(self.m.is_login_successful)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)


class TestAerClubFail(unittest.TestCase):
    def test_login_fail(self):
        m = AerClub(1, 1)
        credentials = {
            'email': 'bad@bad.com',
            'password': '0000'
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
