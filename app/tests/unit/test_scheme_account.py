import json
from unittest import mock, TestCase

from app import AgentException
from app.scheme_account import update_pending_join_account, update_pending_link_account, remove_pending_consents
from app.tasks.resend_consents import ConsentStatus


class TestSchemeAccount(TestCase):
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_link_account(self, mock_intercom_call, mock_requests_delete):
        user_info = {'scheme_account_id': 1}
        with self.assertRaises(AgentException):
            update_pending_link_account(user_info, 'Error Message: error', 'tid123', scheme_slug='scheme_slug')

        self.assertTrue(mock_intercom_call.called)
        self.assertTrue(mock_requests_delete.called)

    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account(self, mock_requests_delete, mock_requests_put, mock_requests_post):
        user_info = {'scheme_account_id': 1}
        update_pending_join_account(user_info, 'success', 'tid123', identifier='12345')
        self.assertTrue(mock_requests_put.called)
        self.assertFalse(mock_requests_delete.called)
        self.assertFalse(mock_requests_post.called)

    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account_error(self, mock_requests_delete, mock_requests_put, mock_requests_post):
        user_info = {'scheme_account_id': 1}
        with self.assertRaises(AgentException):
            update_pending_join_account(user_info, 'Error Message: error', 'tid123', scheme_slug='scheme_slug')

        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)

    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account_raise_exception_false(self, mock_requests_delete, mock_requests_put,
                                                               mock_requests_post):
        user_info = {'scheme_account_id': 1}
        update_pending_join_account(user_info, 'Error Message: error', 'tid123', scheme_slug='scheme_slug',
                                    raise_exception=False)

        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)

    @mock.patch('app.scheme_account.remove_pending_consents')
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account_deletes_consents(self, mock_requests_delete, mock_requests_put,
                                                          mock_requests_post, mock_consents):
        user_info = {'scheme_account_id': 1}
        consent_ids = (1, 2)
        with self.assertRaises(AgentException):
            update_pending_join_account(user_info, 'Error Message: error', 'tid123', scheme_slug='scheme_slug',
                                        consent_ids=consent_ids)

        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)
        self.assertTrue(mock_consents.called)
        self.assertEqual(mock_consents.call_args[0][0], consent_ids)

    @mock.patch('app.scheme_account.requests.put')
    def test_remove_pending_consent(self, mock_requests_put):
        consent_ids = (1, 2)
        headers = {'test header': 'test'}
        remove_pending_consents(consent_ids, {'test header': 'test'})

        self.assertTrue(mock_requests_put.called)
        self.assertEqual(mock_requests_put.call_count, len(consent_ids))

        actual_consent_ids = {str(consent_id) for consent_id in consent_ids}
        call_args_consent_ids = [call_args[0][0][-1:] for call_args in mock_requests_put.call_args_list]
        self.assertEqual(set(actual_consent_ids), set(call_args_consent_ids))

        expected_request_json = json.dumps({'status': ConsentStatus.FAILED})
        for request in mock_requests_put.call_args_list:
            self.assertEqual(request[1], {'data': expected_request_json, 'headers': headers})
