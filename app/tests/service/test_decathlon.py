import unittest
from app.agents.exceptions import LoginError
from app.agents.decathlon import Decathlon
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS


class TestDecathlon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Decathlon(1, 1)
        cls.d.attempt_login(CREDENTIALS['decathlon'])

    def test_login(self):
        self.assertEqual(self.d.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.d.balance()
        schemas.balance(balance)
        self.assertRegex(balance['value_label'], '^£\d*\.\d\d$')


class TestDecathlonFail(unittest.TestCase):
    def test_login_fail(self):
        d = Decathlon(1, 1)
        with self.assertRaises(LoginError) as e:
            d.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
