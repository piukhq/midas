import unittest
from app.agents.shell import Shell
from app.agents import schemas


class TestShell(unittest.TestCase):
    def setUp(self):
        credentials = {
            'user_name': 'chris.gormley2@me.com',
            'password': 'KRHansbrics5',
        }
        self.b = Shell(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)

    def test_transactions(self):
        transactions = self.b.transactions()
        schemas.transactions(transactions)

    def test_balance(self):
        balance = self.b.balance()
        schemas.balance(balance)

if __name__ == '__main__':
    unittest.main()
