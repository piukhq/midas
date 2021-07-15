import unittest
from app.agents.harvey_nichols import HarveyNichols
from app.agents import schemas
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS
from app.agents.exceptions import LoginError
from gaia.user_token import UserTokenStore
from settings import REDIS_URL

cred = dict[str, str]


class TestHarveyNichols(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = HarveyNichols(*AGENT_CLASS_ARGUMENTS)
        cls.h.attempt_login(cred)

    def test_login(self):
        json_result = self.h.login_response.json()["CustomerSignOnResult"]
        self.assertEqual(self.h.login_response.status_code, 200)
        self.assertEqual(json_result["outcome"], "Success")

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)

    def tearDown(self):
        store = UserTokenStore(REDIS_URL)
        store.delete(1)


class TestHarveyNicholsFail(unittest.TestCase):
    def setUp(self):
        self.h = HarveyNichols(*AGENT_CLASS_ARGUMENTS)

    def test_login_fail_no_user(self):
        credentials = {
            "email": "no@user.email",
            "password": "Badpassword02",
        }
        with self.assertRaises(LoginError) as e:
            self.h.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Account does not exist")

    def test_login_bad_password(self):
        credentials = {
            "email": "Bademail",
            "password": "Badpassword02",
        }
        with self.assertRaises(LoginError) as e:
            self.h.attempt_login(credentials)
        self.assertEqual(e.exception.name, "Invalid credentials")


class TestToken(unittest.TestCase):
    def test_invalid_token(self):
        self.h = HarveyNichols(*AGENT_CLASS_ARGUMENTS)

        store = UserTokenStore(REDIS_URL)
        store.set(1, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

        credentials = cred
        credentials["card_number"] = "1000000613736"

        self.h.attempt_login(cred)
        self.h.balance()
        login_json = self.h.login_response.json()["CustomerSignOnResult"]
        self.assertEqual(self.h.login_response.status_code, 200)
        self.assertEqual(login_json["outcome"], "Success")
        self.assertEqual(login_json["errorDetails"], None)


if __name__ == "__main__":
    unittest.main()
