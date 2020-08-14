from app.agents.exceptions import LoginError
from app.agents.harvey_nichols import HarveyNichols
from app.tasks.resend_consents import try_consents
from app.utils import JourneyTypes
from unittest import mock
import json
import unittest
import settings


class MockStore:
    class NoSuchToken(Exception):
        pass

    def __init__(self):
        self._store = {}

    def set(self, *args, **kwargs):
        self._store[args[0]] = args[1]

    def get(self, *args, **kwargs):
        key = args[0]
        if key in self._store:
            return self._store[key]
        else:
            raise self.NoSuchToken


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)


saved_consents_data = {}


class MockedReTryTaskStore:

    def set_task(cls, callback_mod, call_back_func, consents_data):
        global saved_consents_data
        saved_consents_data = consents_data


def mocked_requests_post_200_on_lastretry(*args, **kwargs):
    global saved_consents_data
    if saved_consents_data.get("retries") == 0:
        return MockResponse({"response": "success", "code": 200}, 200)
    return MockResponse(None, 400)


def mocked_requests_post_400(*args, **kwargs):
    return MockResponse(None, 400)


def mocked_requests_post_200(*args, **kwargs):
    return MockResponse({"response": "success", "code": 200}, 200)


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


class TestUserConsents(unittest.TestCase):

    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True

    def tearDown(self):
        settings.CELERY_ALWAYS_EAGER = False

    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_400)
    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_400)
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_harvey_nick_mock_login_fail(self, mock_login, mock_post, mock_put):
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.AGENT_TRIES = 1
        hn.HERMES_CONFIRMATION_TRIES = 1
        hn.scheme_id = 123
        hn.token_store = MockStore()
        credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
            'consents': [
                {"id": 1, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        hn._login(credentials)
        self.assertEqual('https://hn_sso.harveynichols.com/preferences/create', mock_post.call_args_list[0][0][0])

        self.assertEqual('{"enactor_id": "2601507998647", "email_optin": true, "push_optin": false}',
                         mock_post.call_args_list[0][1]["data"])

        self.assertIn('/schemes/user_consent/1', mock_put.call_args_list[0][0][0])
        self.assertEqual('{"status": 2}', mock_put.call_args_list[0][1]['data'])
        self.assertIn('/schemes/user_consent/2', mock_put.call_args_list[1][0][0])
        self.assertEqual('{"status": 2}', mock_put.call_args_list[0][1]['data'])

    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_200_ok)
    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_200)
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_harvey_nick_mock_login_pass(self, mock_login, mock_post, mock_put):
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.AGENT_TRIES = 1
        hn.HERMES_CONFIRMATION_TRIES = 1
        hn.scheme_id = 123
        hn.token_store = MockStore()
        credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
            'consents': [
                {"id": 1, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        hn._login(credentials)
        self.assertEqual('https://hn_sso.harveynichols.com/preferences/create', mock_post.call_args_list[0][0][0])

        self.assertEqual('{"enactor_id": "2601507998647", "email_optin": true, "push_optin": false}',
                         mock_post.call_args_list[0][1]["data"])

        self.assertIn('/schemes/user_consent/1', mock_put.call_args_list[0][0][0])
        self.assertEqual('{"status": 1}', mock_put.call_args_list[0][1]['data'])
        self.assertIn('/schemes/user_consent/2', mock_put.call_args_list[1][0][0])
        self.assertEqual('{"status": 1}', mock_put.call_args_list[0][1]['data'])

    @mock.patch('app.tasks.resend_consents.ReTryTaskStore', side_effect=MockedReTryTaskStore)
    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_200_ok)
    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_200_on_lastretry)
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_harvey_nick_mock_login_retry(self, mock_login, mock_post, mock_put, mock_retry):
        global saved_consents_data
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        saved_consents_data = {}
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.AGENT_TRIES = 3
        hn.HERMES_CONFIRMATION_TRIES = 1
        hn.scheme_id = 123
        hn.token_store = MockStore()
        credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
            'consents': [
                {"id": 1, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        with self.assertLogs() as logs:
            hn._login(credentials)
            self.assertEqual('https://hn_sso.harveynichols.com/preferences/create',
                             mock_post.call_args_list[0][0][0])

            self.assertEqual('{"enactor_id": "2601507998647", "email_optin": true, "push_optin": false}',
                             mock_post.call_args_list[0][1]["data"])

            # after first try should have empty put list as consents not sent (tries == 3)
            self.assertListEqual(mock_put.call_args_list, [])

            self.assertIn("400", logs.output[0])
            self.assertIn("midas_logger", logs.output[0])
            self.assertIn("agent", logs.output[0])
            self.assertTrue(mock_retry.called)
            self.assertFalse(mock_put.called)

            # retry the agent consent 1st time  - should fail
            saved_consents_data["retries"] -= 1
            try_consents(saved_consents_data)
            self.assertListEqual(mock_put.call_args_list, [])

            # retry the agent consent 2nd time  - should succeed ie last retry
            saved_consents_data["retries"] -= 1
            try_consents(saved_consents_data)

            self.assertIn('/schemes/user_consent/1', mock_put.call_args_list[0][0][0])
            self.assertEqual('{"status": 1}', mock_put.call_args_list[0][1]['data'])
            self.assertIn('/schemes/user_consent/2', mock_put.call_args_list[1][0][0])
            self.assertEqual('{"status": 1}', mock_put.call_args_list[0][1]['data'])

    @mock.patch('app.tasks.resend_consents.ReTryTaskStore', side_effect=MockedReTryTaskStore)
    @mock.patch('app.tasks.resend_consents.requests.put', side_effect=mocked_requests_put_200_ok)
    @mock.patch('app.tasks.resend_consents.requests.post', side_effect=mocked_requests_post_400)
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request', side_effect=mock_harvey_nick_post)
    def test_harvey_nick_mock_login_agent_fails(self, mock_login, mock_post, mock_put, mock_retry):
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        hn = HarveyNichols(retry_count=1, user_info=user_info)
        hn.AGENT_TRIES = 3
        hn.HERMES_CONFIRMATION_TRIES = 1
        hn.scheme_id = 123
        hn.token_store = MockStore()
        credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
            'consents': [
                {"id": 1, "slug": "email_optin", "value": True, "created_on": "2018-05-11 12:42"},
                {"id": 2, "slug": "push_optin", "value": False, "created_on": "2018-05-11 12:44"},
            ]

        }
        with self.assertLogs() as logs:
            hn._login(credentials)
            self.assertEqual('https://hn_sso.harveynichols.com/preferences/create',
                             mock_post.call_args_list[0][0][0])

            self.assertEqual('{"enactor_id": "2601507998647", "email_optin": true, "push_optin": false}',
                             mock_post.call_args_list[0][1]["data"])

            # after first try should have empty put list as consents not sent (tries == 3)
            self.assertListEqual(mock_put.call_args_list, [])

            self.assertIn("400", logs.output[0])
            self.assertIn("midas_logger", logs.output[0])
            self.assertIn("agent", logs.output[0])
            self.assertTrue(mock_retry.called)
            self.assertFalse(mock_put.called)

            # retry the agent consent 1st time  - should fail
            saved_consents_data["retries"] -= 1
            try_consents(saved_consents_data)
            self.assertListEqual(mock_put.call_args_list, [])

            # retry the agent consent 2nd time  - should fail again and as last try log set consensts failed
            saved_consents_data["retries"] -= 1
            try_consents(saved_consents_data)

            self.assertIn('/schemes/user_consent/1', mock_put.call_args_list[0][0][0])
            self.assertEqual('{"status": 2}', mock_put.call_args_list[0][1]['data'])
            self.assertIn('/schemes/user_consent/2', mock_put.call_args_list[1][0][0])
            self.assertEqual('{"status": 2}', mock_put.call_args_list[0][1]['data'])


class TestLoginJourneyTypes(unittest.TestCase):
    """
    MER-317 & MER-365

    Harvey Nichols will convert "web only" accounts into full loyalty accounts on signOn.

    Don't allow this during LINK journey.
    """

    def setUp(self):
        self.credentials = {
            'email': 'mytest@localhost.com',
            'password': '12345',
        }
        user_info = {
            'scheme_account_id': 123,
            'status': 'pending'
        }
        self.hn = HarveyNichols(retry_count=1, user_info=user_info)
        self.hn.token_store = MockStore()

    @mock.patch('app.tasks.resend_consents.send_consents')
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request')
    def test_login_join_journey(self, mock_make_request, mock_send_consents):
        self.hn.scheme_id = 101
        self.hn.journey_type = JourneyTypes.UPDATE.value
        mock_make_request.side_effect = [
            MockResponse({
                'CustomerSignOnResult': {
                    'outcome': 'Success',
                    'customerNumber': '2601507998647',
                    'token': '1234'
                }
            }, 200)
        ]

        self.hn.login(self.credentials)
        self.assertEqual(
            'https://loyalty.harveynichols.com/WebCustomerLoyalty/services/CustomerLoyalty/SignOn',
            mock_make_request.call_args_list[0][0][0]
        )

    @mock.patch('app.tasks.resend_consents.send_consents')
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request')
    def test_login_update_journey(self, mock_make_request, mock_send_consents):
        credentials = self.credentials.copy()
        credentials['card_number'] = 'card number'
        self.hn.scheme_id = 101
        self.hn.journey_type = JourneyTypes.UPDATE.value
        mock_make_request.side_effect = [
            MockResponse({
                'CustomerSignOnResult': {
                    'outcome': 'Success',
                    'customerNumber': '2601507998647',
                    'token': '1234'
                }
            }, 200)
        ]

        self.hn.login(credentials)
        self.assertEqual(
            'https://loyalty.harveynichols.com/WebCustomerLoyalty/services/CustomerLoyalty/SignOn',
            mock_make_request.call_args_list[0][0][0]
        )
        self.assertEqual('1234', self.hn.token)

    @mock.patch('app.tasks.resend_consents.send_consents')
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request')
    def test_login_add_journey_loyalty_account_check_valid(self, mock_make_request, mock_send_consents):
        self.hn.journey_type = JourneyTypes.LINK.value
        self.hn.token_store = MockStore()

        mock_make_request.side_effect = [
            # Response from /user/hasloyaltyaccount
            MockResponse({"auth_resp": {"message": "OK"}}, 200),
            # Response from /WebCustomerLoyalty/services/CustomerLoyalty/signOn
            MockResponse({
                'CustomerSignOnResult': {
                    'outcome': 'Success',
                    'customerNumber': '2601507998647',
                    'token': '1234'
                }
            }, 200)
        ]

        self.hn.login(self.credentials)
        self.assertEqual(
            'https://hn_sso.harveynichols.com/user/hasloyaltyaccount',
            mock_make_request.call_args_list[0][0][0]
        )
        self.assertEqual(
            mock_make_request.call_args_list[0][1]["headers"],
            {"Accept": "application/json"})
        submitted_json = mock_make_request.call_args_list[0][1]["json"]
        self.assertEqual(submitted_json, self.credentials)
        self.assertEqual(
            'https://loyalty.harveynichols.com/WebCustomerLoyalty/services/CustomerLoyalty/SignOn',
            mock_make_request.call_args_list[1][0][0]
        )

    @mock.patch('app.tasks.resend_consents.send_consents')
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request')
    def test_login_add_journey_loyalty_account_check_no_cached_token(self, mock_make_request, mock_send_consents):
        self.hn.journey_type = JourneyTypes.LINK.value
        self.hn.scheme_id = 101
        for i, msg in enumerate(
            ["Not found",                       # Web account only
             "User details not authenticated"]  # Bad credentials
        ):
            mock_make_request.side_effect = [
                MockResponse(
                    {"auth_resp": {"message": msg, "status_code": "404"}}, 200
                )
            ]
            self.assertRaises(LoginError, self.hn.login, self.credentials)
            self.assertEqual(
                'https://hn_sso.harveynichols.com/user/hasloyaltyaccount',
                mock_make_request.call_args_list[i][0][0]
            )

    @mock.patch('app.tasks.resend_consents.send_consents')
    @mock.patch('app.agents.harvey_nichols.HarveyNichols.make_request')
    def test_login_add_journey_loyaly_account_check_token_cached(self, mock_make_request, mock_send_consents):
        self.hn.journey_type = JourneyTypes.LINK.value
        self.hn.scheme_id = 101
        self.hn.token_store.set(self.hn.scheme_id, 'a token')

        mock_make_request.side_effect = [
            MockResponse({
                'CustomerSignOnResult': {
                    'outcome': 'Success',
                    'customerNumber': '2601507998647',
                    'token': '1234'
                }
            }, 200)
        ]

        try:
            self.hn.login(self.credentials)
        except LoginError:
            self.fail(f'Unexpected LoginError (JourneyType: LINK)')

        self.assertEqual(
            'https://loyalty.harveynichols.com/WebCustomerLoyalty/services/CustomerLoyalty/SignOn',
            mock_make_request.call_args_list[0][0][0]
        )
