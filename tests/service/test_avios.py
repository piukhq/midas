import unittest
from app.agents.avios import Avios
from tests.service.logins import CREDENTIALS


class TestNectar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Avios(retry_count=1)
        cls.b.attempt_login(CREDENTIALS["nectar"])

    def test_login(self):
        self.assertEqual(self.b.browser.response.status_code, 200)