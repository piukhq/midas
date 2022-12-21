import unittest
from unittest import mock
from unittest.mock import Mock

import settings
from app.agents.schemas import Balance
from app.journeys.view import request_balance, set_iceland_link
from app.scheme_account import JourneyTypes, SchemeAccountStatus


class TestView(unittest.TestCase):
    @mock.patch("app.journeys.view.agent_login", return_value=Mock())
    def test_request_balance_no_balance_result(self, mock_agent_login):
        threads = Mock()
        mock_agent_login.return_value.identifier = None
        mock_agent_login.return_value.balance.return_value = None
        result = request_balance("bpl", {}, 123, "slug", "tid", threads)
        self.assertEqual(result, (None, None, None))

    @mock.patch("app.journeys.view.set_iceland_link")
    @mock.patch("app.publish.balance")
    @mock.patch("app.journeys.view.agent_login", return_value=Mock())
    def test_request_balance_iceland_is_link_if_validate_enabled(
        self, mock_agent_login, mock_publish_balance, mock_set_iceland_link
    ):
        mock_agent_login.return_value.identifier = None
        mock_agent_login.return_value.create_journey = "join"
        user_info = {"status": SchemeAccountStatus.PENDING, "user_set": "123"}
        mock_set_iceland_link.return_value = user_info
        balance = Balance(
            points=0,
            value=0,
            value_label="label",
        )
        mock_agent_login.return_value.balance.return_value = balance
        returned_balance, status, create_journey = request_balance(
            "iceland",
            user_info,
            "123",
            "iceland-bonus-card",
            "tid",
            Mock(),
        )
        mock_publish_balance.assert_called()
        mock_set_iceland_link.assert_called()
        self.assertEqual(status, SchemeAccountStatus.ACTIVE)

    def test_set_iceland_link(self):
        settings.ENABLE_ICELAND_VALIDATE = True
        user_info = {"status": SchemeAccountStatus.PENDING, "journey_type": "not a link journey"}
        user_info = set_iceland_link(user_info)
        self.assertEqual(user_info["journey_type"], JourneyTypes.LINK.value)
        user_info["journey_type"] = "not a link journey"
        settings.ENABLE_ICELAND_VALIDATE = False
        user_info = set_iceland_link(user_info)
        self.assertEqual(user_info["journey_type"], "not a link journey")
