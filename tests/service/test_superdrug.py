import unittest
from app.agents.superdrug import SuperDrug
from urllib.parse import urlsplit
from app.agents import schemas


class TestSuperDrug(unittest.TestCase):
    def setUp(self):
        credentials = {
            'user_name': 'julie.gormley100@gmail.com',
            'password': 'FRHansbrics9'
        }
        self.b = SuperDrug(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)
        self.assertNotEqual(urlsplit(self.b.browser.url).query, 'loginError=true')

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
