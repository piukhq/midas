import unittest
from app.agents.harrods import Harrods
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS
from app.agents import schemas


class TestHarrods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = Harrods(1, 1)
        cls.h.attempt_login(CREDENTIALS['harrods'])

    def test_login(self):
        self.assertEqual(self.h.browser.url, 'https://www.harrods.com/Pages/Account/Secure/AccountHome.aspx')

    def test_balance(self):
        b = self.h.balance()
        schemas.balance(b)
        self.assertRegex(b['value_label'], '^£\d*\.\d\d$')

    def test_transactions(self):
        t = self.h.transactions()
        self.assertTrue(t)
        schemas.transactions(t)


class TestHarrodsFail(unittest.TestCase):
    def test_bad_login(self):
        h = Harrods(1, 1)
        with self.assertRaises(LoginError) as e:
            h.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'STATUS_LOGIN_FAILED')

if __name__ == '__main__':
    unittest.main()