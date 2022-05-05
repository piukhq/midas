from unittest import TestCase, mock

from app.agents.mock_agents import MockAgentHN
from app.journeys.common import get_agent_class


class TestMockAgentHN(TestCase):
    def setUp(self):
        self.retry_count = 0
        self.user_info = {
            "credentials": {
                "consents": [],
                "email": 'user@testbink.com',
                "password": "paSSword"
            },
            "journey_type": 1,
            "scheme_account_id": 123456,
            "status": 0,
            "user_set": '40308'
        }
        self.scheme_slug = 'harvey-nichols-mock'

    def test_get_agent_class(self):
        agent_class = get_agent_class(scheme_slug=self.scheme_slug)
        self.assertEqual(MockAgentHN, agent_class)

    @mock.patch("app.agents.base.Configuration")
    def test_agent_instance_does_not_create_config(self, mock_config):
        MockAgentHN(self.retry_count, self.user_info, scheme_slug=self.scheme_slug)
        self.assertEqual(0, mock_config.call_count)


