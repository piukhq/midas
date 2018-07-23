from app.tasks.resend import ReTryTaskStore
import unittest


class TestUserTokenStore(unittest.TestCase):

    def test_1(self):
        optin_data = {
            "url": "http://localhost:5000",
            "customer_number": "1234567",
            "consents": [
                {"slug": "optin_1", "value": True, "created_on": "2018-05-11 12:42"},
                {"slug": "optin_2", "value": False, "created_on": "2018-05-11 12:44"},

            ],
            "retries": 0,
            "consents_sent": False,
            "notes_sent": False,
            "errors": []
        }
        task = ReTryTaskStore()
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)