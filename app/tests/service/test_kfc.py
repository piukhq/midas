import unittest
from app.agents.kfc import Kfc
from app.agents import schemas
from app.agents.exceptions import LoginError
from app.tests.service.logins import CREDENTIALS


class TestKfc(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.b = Kfc(1, 1)
        cls.b.attempt_login(CREDENTIALS["kfc"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestKfcFail(unittest.TestCase):

    def test_login_fail(self):
        b = Kfc(1, 1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "Invalid credentials")


if __name__ == '__main__':
    unittest.main()
