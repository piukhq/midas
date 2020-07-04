from datetime import timedelta

import arrow
import pytest
from app.tests.service.acteol.fixtures.common import clean_up_user, wasabi


class TestWasabi:
    def test_authenticate_gives_token(self, wasabi):
        """
        The attempt_authenticate() method should result in a token.
        """
        # WHEN
        token = wasabi.authenticate()

        # THEN
        assert isinstance(token, dict)
        assert "token" in token
        assert "timestamp" in token

    def test_refreshes_token(self, wasabi):
        """
        Set the token timeout to a known value to retire it, and expect a new one to have been fetched
        """
        # GIVEN
        wasabi.AUTH_TOKEN_TIMEOUT = 0  # Force retire our token

        # WHEN
        token = wasabi.authenticate()
        token_timestamp = arrow.get(token["timestamp"])
        utc_now = arrow.utcnow()
        diff: timedelta = utc_now - token_timestamp

        # THEN
        assert diff.days == 0
        # A bit arbitrary, but should be less than 5 mins old, as it should have been refreshed
        assert diff.seconds < 300

    def test_register(self, wasabi, clean_up_user):
        # GIVEN
        email = "doesnotexist@bink.com"
        clean_up_user(wasabi=wasabi, email=email)
        credentials = {
            "first_name": "David",
            "last_name": "TestPerson",
            "email": email,
            "phone": "08765543210",
            "postcode": "BN77UU",
        }

        wasabi.register(credentials=credentials)
        clean_up_user(wasabi=wasabi, email=email)

    def test_balance(self, wasabi, clean_up_user):
        # GIVEN
        email = "doesnotexist@bink.com"
        clean_up_user(wasabi=wasabi, email=email)
        credentials = {
            "first_name": "David",
            "last_name": "TestPerson",
            "email": email,
            "phone": "08765543210",
            "postcode": "BN77UU",
        }
        wasabi.register(credentials=credentials)

        # WHEN
        wasabi.attempt_login(credentials=credentials)
        balance = wasabi.balance()

        # THEN
        assert balance["value"] == 0
        assert balance["currency"] == "stamps"
        assert balance["suffix"] == "stamps"
        assert balance["updated_at"]

        clean_up_user(wasabi=wasabi, email=email)


if __name__ == "__main__":
    pytest.main()
