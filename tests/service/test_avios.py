import unittest
from app.agents.avios import Avios


class TestNectar(unittest.TestCase):
    def setUp(self):
        credentials = {
            'username': 'chris.gormley2@me.com',
            'password': 'RZHansbrics5',
        }
        self.b = Avios(retry_count=1)
        self.b.attempt_login(credentials)

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)