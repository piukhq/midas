from app.tasks.resend import ReTryTaskStore
import unittest


class TestUserTokenStore(unittest.TestCase):
    """
    This is not really an automated test.  It kicks off a celery task for integration testing; using redis commander
    or redis cli tool to watch progress of tries. Also by running celery worker and celery beat in Pycharm it is
    possible to monitor and debug the worker task see resend.py

    This test case requires celery worker and celery beat to be running.

    There is a very small chance the test will fail if celery beat causes the task to process the list between
    len_before and len_after. However, this is not a test which should be run automatically
    """

    def test_1(self):
        optin_data = {
            "url": "http://localhost:5000",
            "customer_number": "1234567",
            "consents": [
                {"slug": "optin_1", "value": True, "created_on": "2018-05-11 12:42"},
                {"slug": "optin_2", "value": False, "created_on": "2018-05-11 12:44"},

            ],
            "retries": 10,
            "state": "Consents",
            "errors": []
        }
        task = ReTryTaskStore()
        len_before = task.length
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        len_after = task.length
        self.assertEqual(len_after, len_before+1)


    def test_2(self):
        optin_data = {
            "url": "http://localhost:5000",
            "customer_number": "11111111",
            "consents": [
                {"slug": "optin_1", "value": True, "created_on": "2018-05-11 12:42"},
                {"slug": "optin_2", "value": False, "created_on": "2018-05-11 12:44"},

            ],
            "retries": 10,
            "state": "Consents",
            "errors": []
        }
        task = ReTryTaskStore()
        len_before = task.length
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        optin_data["customer_number"] = "22222222222"
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        len_after = task.length
        self.assertEqual(len_after, len_before + 2)

    def test_3(self):
        optin_data = {
            "url": "http://localhost:5000",
            "customer_number": "33333333",
            "consents": [
                {"slug": "optin_1", "value": True, "created_on": "2018-05-11 12:42"},
                {"slug": "optin_2", "value": False, "created_on": "2018-05-11 12:44"},

            ],
            "retries": 10,
            "state": "Consents",
            "errors": []
        }
        task = ReTryTaskStore()
        len_before = task.length
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        optin_data["customer_number"] = "444444444"
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        optin_data["customer_number"] = "555555555"
        task.set_task("app.agents.harvey_nichols", "try_harvey_nic_optins", optin_data)
        len_after = task.length
        self.assertEqual(len_after, len_before + 3)
