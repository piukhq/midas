import unittest
from app.agents.exceptions import LoginError
from app.agents.choicehotels import ChoiceHotels
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestChoiceHotels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = ChoiceHotels(1, 1)
        cls.m.attempt_login(CREDENTIALS['choicehotels'])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)


class TestChoiceHotelsFail(unittest.TestCase):
    def test_login_fail(self):
        m = ChoiceHotels(1, 1)
        credentials = {
            'username': '3213123123123',
            'password': '3213231312312',
        }
        with self.assertRaises(LoginError) as e:
            m.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
