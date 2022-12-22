import unittest
from unittest import mock
from unittest.mock import Mock

import settings
from app.agents.schemas import Balance
from app.journeys.view import request_balance, set_iceland_user_info_status_and_journey_type
from app.scheme_account import JourneyTypes, SchemeAccountStatus


class TestView(unittest.TestCase):
    @mock.patch("app.journeys.view.agent_login")
    def test_request_balance_no_balance_result(self, mock_agent_login):
        mock_agent_login.return_value.identifier = None
        mock_agent_login.return_value.balance.return_value = None
        result = request_balance("bpl", {}, 123, "slug", "tid", Mock())
        self.assertEqual(result, (None, None, None))

    @mock.patch("app.journeys.view.set_iceland_user_info_status_and_journey_type")
    @mock.patch("app.publish.balance")
    @mock.patch("app.journeys.view.agent_login")
    def test_request_balance_iceland_is_link_if_validate_enabled(
        self, mock_agent_login, mock_publish_balance, mock_set_iceland_journey
    ):
        mock_agent_login.return_value.identifier = None
        mock_agent_login.return_value.create_journey = "join"
        user_info = {"status": SchemeAccountStatus.PENDING, "user_set": "123"}
        mock_set_iceland_journey.return_value = user_info
        mock_agent_login.return_value.balance.return_value = Balance(
            points=0,
            value=0,
            value_label="label",
        )
        returned_balance, status, create_journey = request_balance(
            "iceland",
            user_info,
            "123",
            "iceland-bonus-card",
            "tid",
            Mock(),
        )
        mock_publish_balance.assert_called_with(
            {"points": 0, "value": 0, "value_label": "label", "reward_tier": 0}, "123", "123", "tid"
        )
        mock_set_iceland_journey.assert_called_with({"status": 0, "user_set": "123"})
        mock_agent_login.assert_called_with(
            "iceland", {"status": 0, "user_set": "123"}, scheme_slug="iceland-bonus-card"
        )
        self.assertEqual(status, SchemeAccountStatus.ACTIVE)

    def test_set_iceland_journey_iceland_validate_enabled(self):
        settings.ENABLE_ICELAND_VALIDATE = True
        user_info = {"status": SchemeAccountStatus.PENDING, "journey_type": "not a link journey"}
        user_info = set_iceland_user_info_status_and_journey_type(user_info)
        self.assertEqual(user_info["journey_type"], JourneyTypes.LINK.value)

    def test_set_iceland_journey_iceland_validate_not_enabled(self):
        settings.ENABLE_ICELAND_VALIDATE = False
        user_info = {"status": SchemeAccountStatus.PENDING, "journey_type": "not a link journey"}
        user_info = set_iceland_user_info_status_and_journey_type(user_info)
        self.assertEqual(user_info["journey_type"], "not a link journey")
