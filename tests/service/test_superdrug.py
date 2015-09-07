import unittest
from app.agents.exceptions import LoginError
from app.agents.superdrug import Superdrug
from urllib.parse import urlsplit
from app.agents import schemas
from tests.service.logins import CREDENTIALS


class TestSuperDrug(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Superdrug(retry_count=1)
        cls.b.attempt_login(CREDENTIALS["superdrug"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertNotEqual(urlsplit(self.b.browser.url).query, 'loginError=true')

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)


class TestSuperDrugFail(unittest.TestCase):
    def test_login_fail(self):
        b = Superdrug(retry_count=1)
        with self.assertRaises(LoginError) as e:
            b.attempt_login(CREDENTIALS["bad"])
        self.assertEqual(e.exception.name, "STATUS_LOGIN_FAILED")


if __name__ == '__main__':
    unittest.main()
