import json
import unittest
from unittest import mock
from unittest.mock import MagicMock, Mock

from retry_tasks_lib.enums import RetryTaskStatuses

import app.exceptions as exc
from app.error_handler import handle_retry_task_request_error


class TestErrorHandler(unittest.TestCase):
    @mock.patch("app.error_handler.get_retry_task", return_value=Mock())
    @mock.patch("app.error_handler._handle_request_exception", side_effect=[{}, RetryTaskStatuses.FAILED, None])
    @mock.patch("app.error_handler.update_pending_join_account")
    @mock.patch("app.error_handler.decrypt_credentials", return_value={})
    def test_update_pending_join_called_on_failure(
        self, mock_decrypt, mock_update_pending, mock_handle_exception, mock_retry_task
    ):
        mock_retry_task.return_value.get_params.return_value = {
            "tid": "123",
            "scheme_slug": "iceland",
            "user_info": json.dumps({"credentials": {}}),
        }
        mock_retry_task.update_task = MagicMock()
        mock_retry_task.return_value.task_type.name = "attempt-join"
        rq_job = Mock()
        rq_job.kwargs = {"retry_task_id": 1}
        handle_retry_task_request_error(rq_job, Exception, exc.EndSiteDownError, {})
        self.assertTrue(mock_update_pending.called)
