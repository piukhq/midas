from unittest import TestCase, mock

from soteria.configuration import Configuration

from app.agents.base import JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING
from app.journeys.removed import agent_loyalty_card_removed_from_bink
from app.scheme_account import JourneyTypes


class MockAgentNotImplemented:
    def __init__(self, retry_count, user_info, scheme_slug=None, config=None):
        self.retry_count = retry_count
        self.user_info = user_info
        self.config_handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.scheme_slug = scheme_slug
        self.config = config


class MockAgentImplemented:
    def __init__(self, retry_count, user_info, scheme_slug=None, config=None):
        self.retry_count = retry_count
        self.user_info = user_info
        self.config_handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.scheme_slug = scheme_slug
        self.config = config

    def loyalty_card_removed_bink(self):
        pass


class TestRemovedJourney(TestCase):
    @mock.patch("app.journeys.removed.get_agent_class")
    def test_agent_loyalty_card_removed_bink_not_implemented(self, mock_get_agent):
        mock_get_agent.return_value = MockAgentNotImplemented
        user_info = {"journey_type": JourneyTypes.REMOVED}
        slug = "test.com"
        result = agent_loyalty_card_removed_from_bink(slug, user_info)
        agent_instance = result.get("agent")
        self.assertTrue(mock_get_agent.called)
        mock_get_agent.asser_called_with(slug, user_info)
        self.assertEqual(agent_instance.retry_count, 1)
        self.assertEqual(agent_instance.config_handler_type, Configuration.REMOVED_HANDLER)
        error = result.get("error")
        # We don't raise an exception because most agents will not implement this feature and we don't want
        # to flood sentry - however we log a warning to help implementation
        self.assertIn("object has no attribute 'loyalty_card_removed_bink'", error)

    @mock.patch("app.journeys.removed.get_agent_class")
    def test_agent_loyalty_card_removed_bink_implemented(self, mock_get_agent):
        mock_get_agent.return_value = MockAgentImplemented
        user_info = {"journey_type": JourneyTypes.REMOVED}
        slug = "test.com"
        result = agent_loyalty_card_removed_from_bink(slug, user_info)
        agent_instance = result.get("agent")
        self.assertTrue(mock_get_agent.called)
        mock_get_agent.asser_called_with(slug, user_info)
        self.assertEqual(agent_instance.retry_count, 1)
        self.assertEqual(agent_instance.config_handler_type, Configuration.REMOVED_HANDLER)
        error = result.get("error")
        self.assertEqual(None, error)
