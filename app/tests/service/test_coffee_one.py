import unittest
from app.agents.coffee_one import CoffeeOne
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


class TestCoffeeOne(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = CoffeeOne(1, 1)
        cls.h.attempt_login(CREDENTIALS['coffee-one'])

    def test_login(self):
        self.assertTrue(self.h.is_login_successful)

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)

    def test_transactions(self):
        t = self.h.transactions()
        self.assertIsNotNone(t)
        schemas.transactions(t)


class TestCoffeeOneFail(unittest.TestCase):

    def test_bad_login(self):
        h = CoffeeOne(1, 1)
        credentials = {
            "card_number": '0000000000',
            "pin": "000000"
        }
        with self.assertRaises(LoginError) as e:
            h.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


if __name__ == '__main__':
    unittest.main()
