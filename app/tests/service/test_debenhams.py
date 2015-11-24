import unittest
from app.agents.debenhams import Debenhams
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestDebenhams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Debenhams(1, 1)
        cls.d.attempt_login(CREDENTIALS["debenhams"])

    def test_login(self):
        self.assertEqual(self.d.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.d.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.d.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestDebenhamsFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        credentials = {
            'username': '234234',
            'password': '234234',
            'memorable_date': '01/01/1970',
        }
        d = Debenhams(1, 1)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
