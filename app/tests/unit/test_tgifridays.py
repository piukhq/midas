import unittest
from decimal import Decimal
from unittest import mock
from unittest.mock import MagicMock

import responses
from soteria.configuration import Configuration

from app.agents.schemas import Balance
from app.agents.tgifridays import TGIFridays
from app.exceptions import AccountAlreadyExistsError, NoSuchRecordError, UnknownError
from app.scheme_account import JourneyTypes

CREDENTIALS = {
    "last_name": "Smith",
    "first_name": "John",
    "email": "johnsmith@test.com",
    "password": "password",
    "consents": [{"value": "true"}],
}

OUTBOUND_SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OAUTH_SECURITY,
        "credentials": [
            {
                "value": CREDENTIALS,
            }
        ],
    },
}

SCHEME_ACCOUNT_ID = "422678"
SCHEME_SLUG = "tgi-fridays"
TID = "d271d01a-c430-11ee-9e53-3e22fb277926"
USER_INFO = {
    "user_set": "34390",
    "bink_user_id": "34390",
    "credentials": {
        "email": "success@bink.com",
        "password": "L0yalty!!&B!n4",
        "first_name": "Carla",
        "last_name": "Gouws",
        "consents": [
            {
                "id": 87330,
                "slug": "marketing_email_subscription",
                "value": True,
                "created_on": "2024-02-05T14:14:06.275027+00:00",
                "journey_type": 0,
            }
        ],
    },
    "status": 442,
    "journey_type": 0,
    "scheme_account_id": 422678,
    "channel": "com.bink.wallet",
}

RESPONSE_SIGN_UP_REGISTER = {
    "access_token": {
        "token": "ACCESS_TOKEN_GOES_HERE",
        "seconds_to_expire": None,
        "revoked_at": None,
    },
    "user": {
        "address": "ADDRESS_GOES_HERE",
        "avatar_remote_url": None,
        "birthday": "1999-01-01",
        "communicable_email": "test@example.com",
        "city": "Mountain View",
        "created_at": "2016-03-16T11:40:07+00:00",
        "email": "test@example.com",
        "email_verified": False,
        "facebook_signup": None,
        "favourite_locations": "304155",
        "favourite_store_numbers": "1023",
        "fb_uid": None,
        "first_name": "FIRST_NAME_GOES_HERE",
        "gender": "male",
        "last_name": "LAST_NAME_GOES_HERE",
        "marketing_email_subscription": True,
        "marketing_pn_subscription": True,
        "migrate_status": False,
        "passcode_configured_for_giftcards": False,
        "phone": "1111111111",
        "profile_field_answers": {},
        "referral_code": "REFERRAL_CODE_GOES_HERE",
        "referral_path": "URL_GOES_HERE",
        "secondary_email": "test@example.com",
        "state": "California",
        "superuser": False,
        "terms_and_conditions": True,
        "title": None,
        "updated_at": "2016-03-16T11:40:08+00:00",
        "user_as_barcode": "1111111",
        "user_as_qrcode": "QR_CODE_GOES_HERE",
        "user_code": "P11111111",
        "user_id": 111111111,
        "user_relations": [],
        "zip_code": "30201",
        "anniversary": "2013-07-13",
        "verification_mode": None,
        "apple_signup": None,
        "apple_uid": None,
        "has_generated_fb_email": False,
        "sms_subscription": True,
        "apple_pass_url": "APPLE_PASS_URL_GOES_HERE",
    },
}

RESPONSE_SIGN_UP_REGISTER_ERROR_422_DEVICE_ALREADY_SHARED = {
    "errors": {
        "device_already_shared": [
            "Device already shared with maximum number of guests allowed."
        ]
    }
}
RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL = {
    "errors": {"email": ["Email has already been taken"]}
}

RESPONSE_GET_USER_INFORMATION = {
    "anniversary": None,
    "avatar_remote_url": None,
    "created_at": "2023-04-04T09:05:19Z",
    "email_verified": False,
    "age_verified": False,
    "privacy_policy": True,
    "id": 111111111,
    "updated_at": "2023-09-12T05:39:28Z",
    "test_user": False,
    "user_joined_at": "2023-04-04T09:05:19Z",
    "balance": {
        "banked_rewards": "2.00",
        "membership_level": "Bronze",
        "membership_level_id": 109,
        "net_balance": 2,
        "net_debits": 0,
        "pending_points": 0,
        "points_balance": 0,
        "signup_anniversary_day": "04/04",
        "total_credits": 15,
        "total_debits": "0.0",
        "total_point_credits": 15,
        "total_redeemable_visits": 1,
        "expired_membership_level": "Bronze",
        "total_visits": 0,
        "initial_visits": 1,
        "unredeemed_cards": 0,
    },
    "selected_card_number": None,
    "selected_reward_id": None,
    "selected_discount_amount": None,
    "rewards": [
        {
            "id": 31300354648,
            "created_at": "2023-10-01T18:05:42Z",
            "end_date_tz": "2023-10-05T18:29:59Z",
            "start_date_tz": "2023-10-01T18:05:42Z",
            "updated_at": "2023-10-01T18:05:42Z",
            "image": "IMAGE_URL_GOES_HERE",
            "status": "unredeemed",
            "points": 100,
            "discount_amount": 10,
            "description": "Free Sandwich with Purchase of Chips and Drink",
            "name": "Free Sandwich with Purchase of Chips and Drink",
            "redeemable_properties": "",
        },
        {
            "id": 31300354654,
            "created_at": "2023-10-01T18:05:42Z",
            "end_date_tz": "2023-10-14T18:29:59Z",
            "start_date_tz": "2023-10-01T18:05:42Z",
            "updated_at": "2023-10-01T18:05:42Z",
            "image": "IMAGE_URL_GOES_HERE",
            "status": "unredeemed",
            "points": 100,
            "discount_amount": 10,
            "description": "Free Drinks",
            "name": "Welcome Series Free Gift",
            "redeemable_properties": "",
        },
    ],
    "discount_type": None,
    "allow_multiple": False,
    "apple_pass_url": "APPLE_PASS_URL_GOES_HERE",
    "authentication_token": "AUTHENTICATION_TOKEN_GOES_HERE",
    "favourite_locations": "306082,333070,304374",
    "favourite_store_numbers": "12345,0604,1234",
    "marketing_email_subscription": True,
    "marketing_pn_subscription": True,
    "passcode_configured": False,
    "profile_field_answers": {"test1": "Option 1"},
    "referral_code": "REFERRAL_CODE_GOES_HERE",
    "referral_path": "URL_GOES_HERE",
    "terms_and_conditions": False,
    "title": "",
    "user_as_barcode": "1111111",
    "user_as_qrcode": "QR_CODE_GOES_HERE",
    "user_code": "P11111111",
    "user_id": 111111111,
    "user_relations": [
        {
            "id": 111111111,
            "relation": "spouse",
            "name": "FIRST_NAME_GOES_HERE LAST_NAME_GOES_HERE",
            "birthday": "1999-01-01",
            "created_at": "2023-08-18T12:32:13Z",
            "updated_at": "2023-08-18T12:32:13Z",
        }
    ],
    "work_zip_code": None,
    "preferred_locale": "en",
    "force_password_reset": True,
    "expiration_date": None,
    "sms_subscription": True,
    "phone": "1111111111",
    "migrate_status": False,
    "email_unsubscribe": False,
    "allow_push_notifications": True,
    "facebook_signup": False,
    "communicable_email": "test@example.com",
    "access_token": "ACCESS_TOKEN_GOES_HERE",
    "subscriptions": [
        {"plan_name": "free burger", "pos_meta": "VIP subs", "subscription_id": 123}
    ],
}

RESPONSE_VAULT_SECRETS = ["client_id", "secret"]


class MockSecretClient:
    def get_secret(self, item):
        m = MagicMock()
        setattr(m, "value", "admin_key")
        return m


class TestTGIFridays(unittest.TestCase):
    def setUp(self):
        self.outbound_security_credentials = OUTBOUND_SECURITY_CREDENTIALS
        self.credentials = CREDENTIALS

        with mock.patch("app.agents.base.Configuration") as mock_configuration:
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.outbound_security_credentials
            mock_config_object.integration_service = "SYNC"
            mock_configuration.return_value = mock_config_object
            self.tgi_fridays = TGIFridays(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": JourneyTypes.JOIN,
                    "scheme_account_id": 94531,
                    "channel": "com.bink.wallet",
                },
                scheme_slug="tgi-fridays",
            )
            self.tgi_fridays.base_url = "http://api-reflector/mock/"
            self.tgi_fridays.max_retries = 0

    def test_generate_signature(self):
        uri = "api2/mobile/users"
        body = {
            "client": "client_id",
            "user": {
                "email": "johnsmith@test.com",
                "password": "password",
                "password_confirmation": "password",
                "first_name": "John",
                "last_name": "Smith",
                "marketing_email_subscription": "true",
            },
        }
        secret = "secret"
        assert (
            self.tgi_fridays._generate_signature(uri, body, secret)
            == "24ab8309a8e2de19f5e3f21ad1560deff4a81667d4356037317a9d5800a5cfc7"
        )

    @mock.patch("app.agents.tgifridays.SecretClient", return_value=MockSecretClient())
    def test_get_vault_secrets(self, mock_secret_client) -> None:
        admin_key = self.tgi_fridays._get_vault_secrets(["tgi-fridays-admin-key"])
        assert admin_key == ["admin_key"]

    @responses.activate
    @mock.patch("app.agents.tgifridays.SecretClient", return_value=MockSecretClient())
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_get_user_information(self, mock_base_signal, mock_secret_client) -> None:
        url = f"{self.tgi_fridays.base_url}api2/dashboard/users/info"
        responses.add(
            responses.GET,
            url,
            json=RESPONSE_GET_USER_INFORMATION,
            status=200,
        )
        self.credentials["merchant_identifier"] = "111111111"
        resp = self.tgi_fridays._get_user_information()

        assert resp == RESPONSE_GET_USER_INFORMATION
        assert responses.calls._calls[0].request.headers["Authorization"] == 'Bearer admin_key'
        assert responses.calls._calls[0].request.body == b'{"user_id": "111111111"}'

        assert mock_base_signal.call_count == 1
        mock_base_signal.call_args[0][0] == 'record-http-request'

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_happy_path(
        self, mock_base_signal, mock_tgifridays_signal, mock_get_vault_secrets
    ) -> None:
        url = f"{self.tgi_fridays.base_url}api2/mobile/users"
        responses.add(
            responses.POST,
            url,
            json=RESPONSE_SIGN_UP_REGISTER,
            status=200,
        )

        self.tgi_fridays.join()

        assert mock_base_signal.call_count == 3
        assert mock_tgifridays_signal.call_count == 0

        request = responses.calls._calls[0].request
        assert list(
            map(
                request.headers.get,
                ["User-Agent", "Content-Type", "x-pch-digest"],
            )
        ) == [
            "bink",
            "application/json",
            "5e4fd03ff284fa436b1dcdf3feb946c56f276e7c7e16ac46a61b70330aab116a",
        ]
        assert isinstance(request.headers["punchh-app-device-id"], str)
        assert (
            request.body
            == '{"client": "client_id", "user": {"first_name": "John", "last_name": "Smith", '
            '"email": "johnsmith@test.com", "password": "password", "password_confirmation": "password", '
            '"marketing_email_subscription": "true"}}'
        )

        assert len(responses.calls._calls) == 1
        assert responses.calls._calls[0].response.json() == RESPONSE_SIGN_UP_REGISTER

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_error_422_device_already_shared(
        self, mock_base_signal, mock_tgifridays_signal, mock_get_vault_secrets
    ) -> None:
        url = f"{self.tgi_fridays.base_url}api2/mobile/users"
        responses.add(
            responses.POST,
            url,
            json=RESPONSE_SIGN_UP_REGISTER_ERROR_422_DEVICE_ALREADY_SHARED,
            status=422,
        )

        with self.assertRaises(AccountAlreadyExistsError):
            self.tgi_fridays.join()

        assert mock_base_signal.call_count == 3
        assert mock_tgifridays_signal.call_count == 1

        assert len(responses.calls._calls) == 1
        assert (
            responses.calls._calls[0].response.json()
            == RESPONSE_SIGN_UP_REGISTER_ERROR_422_DEVICE_ALREADY_SHARED
        )

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_error_422_email(
        self, mock_base_signal, mock_tgifridays_signal, mock_get_vault_secrets
    ) -> None:
        url = f"{self.tgi_fridays.base_url}api2/mobile/users"
        responses.add(
            responses.POST,
            url,
            json=RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL,
            status=422,
        )

        with self.assertRaises(AccountAlreadyExistsError):
            self.tgi_fridays.join()

        assert mock_base_signal.call_count == 3
        assert mock_tgifridays_signal.call_count == 1

        assert len(responses.calls._calls) == 1
        assert (
            responses.calls._calls[0].response.json()
            == RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL
        )

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_success(self, mock_base_signal, mock_get_vault_secrets) -> None:
        url = f"{self.tgi_fridays.base_url}api2/dashboard/users/info"
        responses.add(
            responses.GET,
            url,
            json=RESPONSE_GET_USER_INFORMATION,
            status=200,
        )

        self.credentials["merchant_identifier"] = "111111111"
        self.tgi_fridays.login()
        balance = self.tgi_fridays.balance()

        assert balance == Balance(
            points=Decimal("0"),
            value=Decimal("0"),
            value_label="",
            reward_tier=0,
            balance=None,
            vouchers=[],
        )

        assert len(responses.calls._calls) == 1
        assert (
            responses.calls._calls[0].response.json() == RESPONSE_GET_USER_INFORMATION
        )

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_401(self, mock_base_signal, mock_get_vault_secrets) -> None:
        url = f"{self.tgi_fridays.base_url}api2/dashboard/users/info"
        responses.add(
            responses.GET,
            url,
            status=401,
        )

        self.credentials["merchant_identifier"] = "111111111"

        with self.assertRaises(UnknownError):
            self.tgi_fridays.login()

        assert len(responses.calls._calls) == 1

    @responses.activate
    @mock.patch.object(
        TGIFridays, "_get_vault_secrets", return_value=RESPONSE_VAULT_SECRETS
    )
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_422(self, mock_base_signal, mock_get_vault_secrets) -> None:
        url = f"{self.tgi_fridays.base_url}api2/dashboard/users/info"
        responses.add(
            responses.GET,
            url,
            status=404,
        )

        self.credentials["merchant_identifier"] = "111111111"

        with self.assertRaises(NoSuchRecordError):
            self.tgi_fridays.login()

        assert len(responses.calls._calls) == 1
