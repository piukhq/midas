from app.tasks.resend_consents import send_consents
from app.agents.harvey_nichols import HarveyNichols
from unittest import mock
import unittest
import json


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)


def mocked_requests_post_400(*args, **kwargs):
    return MockResponse(None, 400)


def mocked_requests_post_200(*args, **kwargs):
    return MockResponse(None, 200)


def mocked_requests_put_400(*args, **kwargs):
    return MockResponse(None, 400)


def mocked_requests_put_200_fail(*args, **kwargs):
    return MockResponse({"response": "failure", "code": 404}, 200)


def mocked_requests_put_200_ok(*args, **kwargs):
    return MockResponse({"response": "success", "code": 200}, 200)


def mock_harvey_nick_post(*args, **kwargs):
    return MockResponse({'CustomerSignOnResult': {'outcome': 'Success',
                                                  'customerNumber': '2601507998647',
                                                  'token': '1234'
                                                  }}, 200)


class TestUserTokenStore(unittest.TestCase):
    """
    This is not really an automated test.  It kicks off a celery task for integration testing; using redis commander
    or redis cli tool to watch progress of tries. Also by running celery worker and celery beat in Pycharm it is
    possible to monitor and debug the worker task see resend.py

    This test case requires celery worker and celery beat to be running.

    There is a very small chance the test will fail if celery beat causes the task to process the list between
    len_before and len_after. However, this is not a test which should be run automatically
    """

    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_200)
    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_200_ok)
    def test_1(self, mock_put, mock_post):

        consents = [
                {"id": 1, "slug": "optin_1", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "optin_2", "value": False, "created_on": "2018-05-11 12:44"},

        ]

        hn_post_message = {"enactor_id": '1234567'}
        confirm_dic = {}

        for consent in consents:
            hn_post_message[consent['slug']] = consent['value']
            confirm_dic[consent['id']] = 10  # retries per confirm to hermes put if 0 will not confirm!

        headers = {"Content-Type": "application/json; charset=utf-8"}

        # function "agent_consent_response"
        # callback_function can be set to change default function

        send_consents({
            "url": "http://localhost:5000",
            "headers": headers,
            "message": json.dumps(hn_post_message),
            "agent_tries": 10,
            "confirm_tries": confirm_dic
        })

        self.assertEqual(
            mock.call('http://localhost:5000',
                      headers={'Content-Type': 'application/json; charset=utf-8'},
                      data='{"enactor_id": "1234567", "optin_1": true, "optin_2": false}',
                      timeout=10),
            mock_post.call_args_list[0])
        self.assertEqual('http://127.0.0.1:8000/schemes/userconsent/1', mock_put.call_args_list[0][0][0])
        self.assertEqual('http://127.0.0.1:8000/schemes/userconsent/2', mock_put.call_args_list[1][0][0])
        print(mock_put.call_args_list)

    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_400)
    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_400)
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_HarveyNick_mock_login_fail(self, mock_login, mock_post, mock_put):
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.scheme_id = 123
        credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
            'consents': [
                {"id": 1, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        hn._login(credentials)
        self.assertEqual('https://admin.uat.harveynichols.com/preferences/create', mock_post.call_args_list[0][0][0])

        self.assertEqual('{"enactor_id": "2601507998647", "email_optin": true, "push_optin": false}',
                         mock_post.call_args_list[0][1]["data"])

        print(mock_put.call_args_list)
        # self.assertEqual('http://127.0.0.1:8000/schemes/userconsent/1', mock_put.call_args_list[0][0][0])
        # self.assertEqual('http://127.0.0.1:8000/schemes/userconsent/2', mock_put.call_args_list[1][0][0])

    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_HarveyNick_mock_login_real(self, mock_login):
        user_info = {
            'scheme_account_id': 3,
            'status': 'pending'
        }
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.scheme_id = 1
        credentials = {
            'email': 'mmarsh@bink.com',
            'password': 'SDxyh!wed12X',
            'card_number': '2601507998647',
            'consents': [
                {"id": 6, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 7, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        hn._login(credentials)
