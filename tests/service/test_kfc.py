import unittest
from app.agents.kfc import Kfc
from app.agents import schemas
from app.agents.exceptions import LoginError
from tests.service.logins import CREDENTIALS


class TestKfc(unittest.TestCase):
    def setUp(self):
        self.b = Kfc(retry_count=1)
        self.b.attempt_login(CREDENTIALS["kfc"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestKfcFail(unittest.TestCase):
    def test_login_fail(self):
        b = Kfc(retry_count=1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")

if __name__ == '__main__':
    unittest.main()
