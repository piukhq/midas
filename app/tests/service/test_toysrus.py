import unittest
from app.agents.toysrus import Toysrus
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestToysrus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Toysrus(1, 1)
        cls.t.attempt_login(CREDENTIALS["toysrus"])

    def test_login(self):
        self.assertEqual(self.t.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.t.balance()
        schemas.balance(balance)


class TestToysrusFail(unittest.TestCase):
    def test_login_bad_credentials(self):
        credentials = CREDENTIALS["bad"]
        t = Toysrus(1, 1)
        with self.assertRaises(LoginError) as e:
            t.attempt_login(credentials)
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")


if __name__ == '__main__':
    unittest.main()
