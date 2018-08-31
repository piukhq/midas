import unittest
from app.agents.debenhams import Debenhams
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS, AGENT_CLASS_ARGUMENTS


class TestDebenhams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Debenhams(*AGENT_CLASS_ARGUMENTS)
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
    def test_login_bad_email(self):
        credentials = {
            'email': '234234',
            'password': '234234',
        }
        d = Debenhams(*AGENT_CLASS_ARGUMENTS)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")

    # -------------------------------------------------------------- #
    # Debenhams currently locks out accounts that run this test.     #
    # if needed use a fresh account to test manually.                #
    # -------------------------------------------------------------- #

    # def test_login_bad_password(self):
    #     credentials = {
    #         'email': 'loyaltyangelsc@gmail.com',
    #         'password': '234234',
    #     }
    #     d = Debenhams(*AGENT_CLASS_ARGUMENTS)
    #     with self.assertRaises(LoginError) as e:
    #         d.attempt_login(credentials)
    #     self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
