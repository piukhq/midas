import unittest
from app.agents.exceptions import LoginError
from app.agents.the_club import TheClub
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestMacdonaldHotels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = TheClub(1, 1)
        cls.b.attempt_login(CREDENTIALS["the-club"])

    def test_login(self):
        self.assertTrue(self.b.is_login_successful)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestMacdonaldHotelsFail(unittest.TestCase):
    def test_login_fail(self):
        b = TheClub(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
