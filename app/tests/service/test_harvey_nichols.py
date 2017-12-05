import unittest
from app.agents.harvey_nichols import HarveyNichols
from app.agents import schemas
from app.tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError
from gaia.user_token import UserTokenStore


class TestHarveyNichols(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h = HarveyNichols(1, 1)
        cls.h.attempt_login(CREDENTIALS['harvey-nichols'])

    def test_login(self):
        json_result = self.h.login_response.json()['CustomerSignOnResult']
        self.assertEqual(self.h.login_response.status_code, 200)
        self.assertEqual(json_result['outcome'], 'Success')

    def test_transactions(self):
        transactions = self.h.transactions()
        self.assertIsNotNone(transactions)
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.h.balance()
        schemas.balance(balance)

    def tearDown(self):
        store = UserTokenStore('redis://localhost:6379/4')
        store.delete(1)


class TestHarveyNicholsFail(unittest.TestCase):
    def setUp(self):
        self.h = HarveyNichols(1, 1)

    def test_login_fail_no_user(self):
        credentials = {
            'email': 'no@user.email',
            'password': 'Badpassword02',
        }
        with self.assertRaises(LoginError) as e:
            self.h.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Account does not exist')

    def test_login_bad_password(self):
        credentials = {
            'email': CREDENTIALS['harvey-nichols']['email'],
            'password': 'Badpassword02',
        }
        with self.assertRaises(LoginError) as e:
            self.h.attempt_login(credentials)
        self.assertEqual(e.exception.name, 'Invalid credentials')


class TestToken(unittest.TestCase):

    def test_invalid_token(self):
        self.h = HarveyNichols(1, 1)

        store = UserTokenStore('redis://localhost:6379/4')
        store.set(1, '1')

        credentials = CREDENTIALS['harvey-nichols']
        credentials['card_number'] = "1000000613736"

        self.h.attempt_login(CREDENTIALS['harvey-nichols'])

        json_result = self.h.login_response.json()['CustomerSignOnResult']
        self.assertEqual(self.h.login_response.status_code, 200)
        self.assertEqual(json_result['outcome'], 'Success')


if __name__ == '__main__':
    unittest.main()
