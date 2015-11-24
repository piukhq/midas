import unittest
from app.agents.paperchase import Paperchase
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestPaperchase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Paperchase(1, 1)
        cls.b.attempt_login(CREDENTIALS['treat-me'])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestPaperchaseFail(unittest.TestCase):
    def test_login_fail(self):
        b = Paperchase(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS['bad'])
        self.assertEqual(e.exception.name, 'Invalid credentials')

if __name__ == '__main__':
    unittest.main()
