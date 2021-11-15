import json
from unittest import mock
from unittest.mock import MagicMock
import settings
import arrow
from flask_testing import TestCase

settings.API_AUTH_ENABLED = False
from app.agents.squaremeal import Squaremeal
from app.api import create_app


class TestSquaremeal(TestCase):
    def create_app(self):
        return create_app(self)

    def setUp(self):
        self.security_credentials = {
            "outbound": {
                "credentials": [
                    {
                        "value": {
                            "url": "http://fake.com",
                            "secondary-key": "12345678",
                            "client-id": "123",
                            "client-secret": "123a6ba",
                            "scope": "dunno"
                        },
                    }
                ]
            }
        }
        self.credentials = {
            "first_name": "Fake",
            "last_name": "Name",
            "email": "email@domain.com",
            "password": "pAsSw0rD",
            "consents": [{"id": 11738, "slug": "Subscription", "value": False, "created_on": "1996-09-26T00:00:00"}],
        }

        with mock.patch("app.agents.squaremeal.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.security_credentials
            mock_configuration.return_value = mock_config_object
            self.squaremeal = Squaremeal(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": 0,
                    "scheme_account_id": 94532,
                    "channel": "com.bink.wallet",
                },
                scheme_slug="squaremeal",
            )
            self.squaremeal.base_url = "https://sm-uk.azure-api.net/bink-dev/api/v1/account/"

    @mock.patch("app.messaging.queue")
    @mock.patch("app.resources.decrypt_credentials")
    @mock.patch("app.agents.squaremeal.Squaremeal.authenticate", return_value="fake-123")
    def test_join(self, mock_authenticate, mock_decrypt_credentials, mock_queue):
        mock_decrypt_credentials.return_value = self.credentials
        url = "/squaremeal-restaurant-rewards/register"
        data = {
            "scheme_account_id": 1,
            "credentials": self.security_credentials,
            "user_id": 1,
            "status": 0,
            "journey_type": 1,
            "channel": "bink",
        }
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "success"})

    @mock.patch("app.agents.squaremeal.Configuration")
    def test_get_security_credentials(self, mock_config):
        mock_config.return_value = self.security_credentials
        self.assertEqual(self.squaremeal.auth_url, "http://fake.com")
        self.assertEqual(self.squaremeal.secondary_key, "12345678")

    @mock.patch("app.agents.squaremeal.Squaremeal._store_token")
    @mock.patch("app.agents.squaremeal.Squaremeal.token_store.get", return_value="fake-123")
    @mock.patch("app.agents.squaremeal.Squaremeal._refresh_token", return_value="fake-123")
    def test_authenticate(self, mock_refresh_token, mock_token_store, mock_store_token):
        current_timestamp = (arrow.utcnow().int_timestamp,)
        mock_token_store.return_value = json.dumps({"timestamp": current_timestamp, "sm_access_token": "fake-123"})
        self.assertEqual(self.squaremeal.authenticate(), "fake-123")

        # Ensure all the necessary methods called when token expired
        self.squaremeal.AUTH_TOKEN_TIMEOUT = 0
        self.squaremeal.authenticate()
        mock_refresh_token.assert_called()
        mock_store_token.assert_called()
