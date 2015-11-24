import unittest
from app.agents.mandco import MandCo
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestMandCo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = MandCo(1, 1)
        cls.m.attempt_login(CREDENTIALS["mandco"])

    def test_login(self):
        self.assertEqual(self.m.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.m.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.m.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ £5 reward voucher[s]?$|^$')


class TestMandCoFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        m = MandCo(1, 1)
        with self.assertRaises(LoginError) as e:
            m.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
