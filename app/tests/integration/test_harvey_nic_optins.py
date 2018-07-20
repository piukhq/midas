from app.agents.harvey_nichols import retry_try_havery_nic_optins
import unittest

class TestUserTokenStore(unittest.TestCase):

    def test_1(self):
        optin_data = {
            "url": "localhost:5000",
            "customer_number": "1234567",
            "consents": {"v1":"v1","v2":"v2"},
            "retries": 0,
            "consents_sent": False,
            "notes_sent": False
        }

        retry_try_havery_nic_optins(optin_data)