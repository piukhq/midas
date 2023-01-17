from unittest import TestCase, mock

import pytest
from soteria.configuration import Configuration

from app.agents.acteol import Wasabi
from app.exceptions import NoSuchRecordError, RetryLimitReachedError, UnknownError, ValidationError
from app.journeys.common import agent_login
from app.scheme_account import JourneyTypes


class TestCommon(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config = mock.MagicMock()
        cls.mock_config.merchant_url = "https://wasabiuat.test.wasabiworld.co.uk/"
        cls.mock_config.security_credentials = {
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {"password": "paSSword", "username": "username@bink.com"},
                    }
                ],
            },
        }

        cls.user_info = {
            "scheme_account_id": 1,
            "status": 1,
            "user_set": "1,2",
            "bink_user_id": 1,
            "journey_type": JourneyTypes.LINK.value,
            "credentials": {"card_number": "1048172852", "consents": [], "email": "fail@unknown.com"},
            "channel": "com.bink.wallet",
        }
        cls.scheme_slug = "wasabi-club"

    @mock.patch("app.redis_retry.get_count", return_value=0)
    @mock.patch("app.redis_retry.get_key", return_value="some_key")
    @mock.patch.object(Wasabi, "attempt_login")
    def test_agent_login_error_system_action_required_is_false(self, mock_attempt_login, mock_get_key, mock_get_count):
        mock_attempt_login.side_effect = ValidationError(message="Invalid Member Number")
        with mock.patch("app.agents.base.Configuration", return_value=self.mock_config):
            agent_instance = agent_login(Wasabi, self.user_info, self.scheme_slug, from_join=True)

        assert isinstance(agent_instance, Wasabi)

    @mock.patch("app.redis_retry.get_count", return_value=0)
    @mock.patch("app.redis_retry.get_key", return_value="some_key")
    @mock.patch.object(Wasabi, "attempt_login")
    def test_agent_login_error_system_action_required_is_true(self, mock_attempt_login, mock_get_key, mock_get_count):
        mock_attempt_login.side_effect = NoSuchRecordError()
        with pytest.raises(NoSuchRecordError) as e:
            with mock.patch("app.agents.base.Configuration", return_value=self.mock_config):
                agent_login(Wasabi, self.user_info, self.scheme_slug, from_join=True)

        assert e.value.system_action_required is True
        assert e.value.name == "Account does not exist"

    @mock.patch("app.redis_retry.get_count", return_value=0)
    @mock.patch("app.redis_retry.get_key", return_value="some_key")
    @mock.patch.object(Wasabi, "attempt_login")
    def test_agent_login_raises_unknown_error(self, mock_attempt_login, mock_get_key, mock_get_count):
        mock_attempt_login.side_effect = Exception
        with pytest.raises(UnknownError):
            with mock.patch("app.agents.base.Configuration", return_value=self.mock_config):
                agent_login(Wasabi, self.user_info, self.scheme_slug, from_join=True)

    @mock.patch("app.redis_retry.max_out_count")
    @mock.patch("app.redis_retry.get_count", return_value=0)
    @mock.patch("app.redis_retry.get_key", return_value="some_key")
    @mock.patch.object(Wasabi, "attempt_login")
    def test_agent_login_raises_retry_limit_reached_error(
        self, mock_attempt_login, mock_get_key, mock_count, mock_max_out_count
    ):
        mock_attempt_login.side_effect = RetryLimitReachedError()
        with pytest.raises(RetryLimitReachedError) as e:
            with mock.patch("app.agents.base.Configuration", return_value=self.mock_config):
                agent_login(Wasabi, self.user_info, self.scheme_slug, from_join=True)
                assert mock_max_out_count.called_with("some_key", 2)
                assert e.value.name == "Retry limit reached"
