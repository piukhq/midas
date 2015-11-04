import unittest
from app.agents.exceptions import LoginError
from app.agents.beefeater import Beefeater, format_voucher_count
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestBeefeater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Beefeater(1, 1)
        cls.b.attempt_login(CREDENTIALS['beefeater'])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        self.assertTrue(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^\d+ discount voucher[s]?$')

    def test_format_voucher_count(self):
        self.assertEqual('0 discount vouchers', format_voucher_count(0))
        self.assertEqual('1 discount voucher', format_voucher_count(1))
        self.assertEqual('2 discount vouchers', format_voucher_count(2))


class TestBeefeaterFail(unittest.TestCase):
    def test_login_fail(self):
        b = Beefeater(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()
