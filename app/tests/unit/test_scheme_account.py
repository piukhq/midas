from unittest import mock, TestCase

from app import AgentException
from app.scheme_account import update_pending_join_account, update_pending_link_account


class TestSchemeAccount(TestCase):
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.delete')
    @mock.patch('app.scheme_account.raise_event')
    def test_update_pending_link_account(self, mock_intercom_call, mock_requests_delete, mock_requests_post):
        intercom_data = {
            'user_id': 'userid12345',
            'user_email': 'test@email.com',
            'metadata': {'scheme': 'scheme_slug'}
        }
        with self.assertRaises(AgentException):
            update_pending_link_account('123', 'Error Message: error', 'tid123', intercom_data=intercom_data)

        self.assertTrue(mock_intercom_call.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)

    @mock.patch('app.scheme_account.raise_event')
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account(self, mock_requests_delete, mock_requests_put, mock_requests_post,
                                         mock_intercom_call):

        update_pending_join_account('123', 'success', 'tid123', identifier='12345')
        self.assertTrue(mock_requests_put.called)
        self.assertFalse(mock_requests_delete.called)
        self.assertFalse(mock_requests_post.called)
        self.assertFalse(mock_intercom_call.called)

    @mock.patch('app.scheme_account.raise_event')
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account_error(self, mock_requests_delete, mock_requests_put, mock_requests_post,
                                               mock_intercom_call):

        intercom_data = {
            'user_id': 'userid12345',
            'user_email': 'test@email.com',
            'metadata': {'scheme': 'scheme_slug'}
        }
        with self.assertRaises(AgentException):
            update_pending_join_account('123', 'Error Message: error', 'tid123', intercom_data=intercom_data)

        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)
        self.assertTrue(mock_intercom_call.called)

    @mock.patch('app.scheme_account.raise_event')
    @mock.patch('app.scheme_account.requests.post')
    @mock.patch('app.scheme_account.requests.put')
    @mock.patch('app.scheme_account.requests.delete')
    def test_update_pending_join_account_raise_exception_false(self, mock_requests_delete, mock_requests_put,
                                                               mock_requests_post, mock_intercom_call):

        intercom_data = {
            'user_id': 'userid12345',
            'user_email': 'test@email.com',
            'metadata': {'scheme': 'scheme_slug'}
        }
        update_pending_join_account('123', 'Error Message: error', 'tid123', intercom_data=intercom_data,
                                    raise_exception=False)

        self.assertFalse(mock_requests_put.called)
        self.assertTrue(mock_requests_delete.called)
        self.assertTrue(mock_requests_post.called)
        self.assertTrue(mock_intercom_call.called)
