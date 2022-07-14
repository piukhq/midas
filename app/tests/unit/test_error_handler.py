import json
import unittest
from unittest import mock
from unittest.mock import MagicMock, Mock

import app.exceptions as exc
from app.encryption import AESCipher
from app.error_handler import handle_retry_task_request_error
from app.models import CallbackStatuses, RetryTaskStatuses
from app.tests.unit.test_resources import local_aes_key


def encrypted_credentials():
    aes = AESCipher(local_aes_key.encode())
    return aes.encrypt(json.dumps({})).decode()


class TestErrorHandler(unittest.TestCase):
    @mock.patch("app.error_handler.delete_task")
    @mock.patch("app.error_handler.get_task", return_value=Mock())
    @mock.patch("app.error_handler._handle_request_exception", side_effect=[{}, RetryTaskStatuses.FAILED, None])
    @mock.patch("app.error_handler.update_pending_join_account")
    @mock.patch("app.error_handler.decrypt_credentials", return_value={})
    def test_update_pending_join_called_on_failure(
        self, mock_decrypt, mock_update_pending, mock_handle_exception, mock_retry_task, mock_delete
    ):
        mock_retry_task.return_value.request_data = json.dumps(
            {
                "tid": "123",
                "scheme_slug": "iceland",
                "credentials": encrypted_credentials(),
            }
        )
        mock_retry_task.update_task = MagicMock()
        mock_retry_task.return_value.journey_type = "attempt-join"
        mock_retry_task.return_value.callback_status = CallbackStatuses.NO_CALLBACK
        rq_job = Mock()
        rq_job.args = [1]
        handle_retry_task_request_error(rq_job, Exception, exc.EndSiteDownError, {})
        self.assertTrue(mock_update_pending.called)
