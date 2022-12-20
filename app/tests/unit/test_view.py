import unittest
from unittest import mock
from unittest.mock import Mock

from app.journeys.view import request_balance


class TestView(unittest.TestCase):
    @mock.patch("app.journeys.view.agent_login", return_value=Mock())
    def test_request_balance_no_balance_result(self, mock_agent_instance):
        threads = Mock()
        mock_agent_instance.return_value.identifier = None
        mock_agent_instance.return_value.balance.return_value = None
        result = request_balance("bpl", {}, 123, "slug", "tid", threads)
        self.assertEqual(result, (None, None, None))
