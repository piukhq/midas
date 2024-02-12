import unittest
from decimal import Decimal
from unittest import mock

import pytest
import responses
from soteria.configuration import Configuration

import settings
from app.agents.schemas import Balance
from app.agents.tgifridays import TGIFridays
from app.exceptions import AccountAlreadyExistsError, NoSuchRecordError, UnknownError
from app.scheme_account import JourneyTypes

CREDENTIALS = {
    "email": "johnsmith@test.com",
    "password": "password",
    "first_name": "John",
    "last_name": "Smith",
    "consents": [
        {
            "id": 87330,
            "slug": "marketing_email_subscription",
            "value": True,
            "created_on": "2024-02-05T14:14:06.275027+00:00",
            "journey_type": 0,
        }
    ],
}

OUTBOUND_SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OAUTH_SECURITY,
        "credentials": [
            {
                "value": {
                    "client_id": "client_id",
                    "secret": "secret",
                    "admin_key": "admin_key",
                },
            }
        ],
    },
}

SCHEME_SLUG = "tgi-fridays"
USER_INFO = {
    "user_set": "34390",
    "bink_user_id": "34390",
    "credentials": CREDENTIALS,
    "status": 442,
    "journey_type": JourneyTypes.JOIN,
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
    "errors": {"device_already_shared": ["Device already shared with maximum number of guests allowed."]}
}
RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL = {"errors": {"email": ["Email has already been taken"]}}

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
    "subscriptions": [{"plan_name": "free burger", "pos_meta": "VIP subs", "subscription_id": 123}],
}


class TestTGIFridays(unittest.TestCase):
    def setUp(self):
        self.credentials = CREDENTIALS

        with mock.patch("app.agents.base.Configuration") as mock_configuration:
            mock_config_object = mock.MagicMock()
            mock_config_object.security_credentials = OUTBOUND_SECURITY_CREDENTIALS
            mock_config_object.integration_service = "SYNC"
            mock_configuration.return_value = mock_config_object
            self.tgi_fridays = TGIFridays(
                retry_count=1,
                user_info=USER_INFO,
                scheme_slug="tgi-fridays",
            )
            self.tgi_fridays.base_url = "http://api-reflector/mock/"
            self.tgi_fridays.max_retries = 0

    def test_generate_signature(self) -> None:
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

    def test_generate_punchh_app_device_id(self) -> None:
        assert self.tgi_fridays._generate_punchh_app_device_id() == "e25vrke74gx9mwqpz0g6pjy38zo1dq0l"

    @responses.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_get_user_information(
        self,
        mock_base_signal,
    ) -> None:
        url = f"{self.tgi_fridays.base_url}api2/dashboard/users/info"
        responses.add(
            responses.GET,
            url,
            json=RESPONSE_GET_USER_INFORMATION,
            status=200,
        )
        self.tgi_fridays.credentials["merchant_identifier"] = 111111111
        resp = self.tgi_fridays._get_user_information()

        assert resp == RESPONSE_GET_USER_INFORMATION
        assert responses.calls._calls[0].request.headers["Authorization"] == "Bearer admin_key"
        assert responses.calls._calls[0].request.body == b'{"user_id": 111111111}'

        mock_base_signal.call_args_list = [
            mock.call("send-audit-request"),
            mock.call("send-audit-response"),
            mock.call("record-http-request"),
        ]

    @responses.activate
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_happy_path(
        self,
        mock_base_signal,
        mock_tgifridays_signal,
    ) -> None:
        responses.add(
            responses.POST,
            f"{self.tgi_fridays.base_url}api2/mobile/users",
            json=RESPONSE_SIGN_UP_REGISTER,
            status=200,
        )
        responses.add(
            responses.PUT,
            f"{settings.HERMES_URL}/schemes/accounts/{self.tgi_fridays.user_info['scheme_account_id']}/credentials",
            status=200,
        )

        self.tgi_fridays.join()

        assert mock_base_signal.call_args_list == [
            mock.call("send-audit-request"),
            mock.call("send-audit-response"),
            mock.call("record-http-request"),
        ]
        assert mock_tgifridays_signal.call_args_list == [mock.call("join-success")]

        request = responses.calls._calls[0].request
        assert list(
            map(
                request.headers.get,
                ["User-Agent", "Content-Type", "x-pch-digest", "punchh-app-device-id"],
            )
        ) == [
            "bink",
            "application/json",
            "b028e9f3d60e161d6514c6d58c75638717b016c611f469a36027096c6247b557",
            "e25vrke74gx9mwqpz0g6pjy38zo1dq0l",
        ]
        assert (
            request.body
            == b'{"client": "client_id", "user": {"first_name": "John", "last_name": "Smith", "email": "johnsmith@test.com", "password": "password", "password_confirmation": "password", "marketing_email_subscription": true}}'
        )

        assert len(responses.calls._calls) == 1
        assert responses.calls._calls[0].response.json() == RESPONSE_SIGN_UP_REGISTER  # type:ignore

        assert self.tgi_fridays.identifier == {"merchant_identifier": 111111111}
        assert self.tgi_fridays.credentials["merchant_identifier"] == 111111111

        assert self.tgi_fridays.identifier == {
            "card_number": "4219ccc6-33bc-46f4-a1a9-996a2b3dc53e",
            "merchant_identifier": 111111111,
        }

    @responses.activate
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_error_422_device_already_shared(
        self,
        mock_base_signal,
        mock_tgifridays_signal,
    ) -> None:
        responses.add(
            responses.POST,
            url=f"{self.tgi_fridays.base_url}api2/mobile/users",
            json=RESPONSE_SIGN_UP_REGISTER_ERROR_422_DEVICE_ALREADY_SHARED,
            status=422,
        )

        with pytest.raises(AccountAlreadyExistsError):
            self.tgi_fridays.join()

        assert mock_base_signal.call_args_list == [
            mock.call("send-audit-request"),
            mock.call("send-audit-response"),
            mock.call("record-http-request"),
            mock.call("request-fail"),
        ]
        assert mock_tgifridays_signal.call_args_list == [mock.call("join-fail")]

        assert len(responses.calls._calls) == 1
        assert responses.calls._calls[0].response.json() == RESPONSE_SIGN_UP_REGISTER_ERROR_422_DEVICE_ALREADY_SHARED  # type:ignore

    @responses.activate
    @mock.patch("app.agents.tgifridays.signal", autospec=True)
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_join_error_422_email(
        self,
        mock_base_signal,
        mock_tgifridays_signal,
    ) -> None:
        responses.add(
            responses.POST,
            url=f"{self.tgi_fridays.base_url}api2/mobile/users",
            json=RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL,
            status=422,
        )

        with pytest.raises(AccountAlreadyExistsError):
            self.tgi_fridays.join()

        assert mock_base_signal.call_args_list == [
            mock.call("send-audit-request"),
            mock.call("send-audit-response"),
            mock.call("record-http-request"),
            mock.call("request-fail"),
        ]
        assert mock_tgifridays_signal.call_args_list == [mock.call("join-fail")]

        assert len(responses.calls._calls) == 1
        assert responses.calls._calls[0].response.json() == RESPONSE_SIGN_UP_REGISTER_ERROR_422_EMAIL  # type:ignore

    @responses.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_from_join_success(
        self,
        mock_base_signal,
    ) -> None:
        responses.add(
            responses.GET,
            url=f"{self.tgi_fridays.base_url}api2/dashboard/users/info",
            json=RESPONSE_GET_USER_INFORMATION,
            status=200,
        )

        self.tgi_fridays.credentials["merchant_identifier"] = 111111111
        self.tgi_fridays.user_info["from_join"] = True
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
        assert responses.calls._calls[0].response.json() == RESPONSE_GET_USER_INFORMATION  # type:ignore

    @responses.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_from_join_401(
        self,
        mock_base_signal,
    ) -> None:
        responses.add(
            responses.GET,
            f"{self.tgi_fridays.base_url}api2/dashboard/users/info",
            status=401,
        )

        self.tgi_fridays.credentials["merchant_identifier"] = 111111111
        self.tgi_fridays.user_info["from_join"] = True

        with pytest.raises(UnknownError):
            self.tgi_fridays.login()

        assert len(responses.calls._calls) == 1

    @responses.activate
    @mock.patch("app.agents.base.signal", autospec=True)
    def test_balance_from_join_422(
        self,
        mock_base_signal,
    ) -> None:
        responses.add(
            responses.GET,
            f"{self.tgi_fridays.base_url}api2/dashboard/users/info",
            status=404,
        )

        self.tgi_fridays.credentials["merchant_identifier"] = 111111111
        self.tgi_fridays.user_info["from_join"] = True

        with pytest.raises(NoSuchRecordError):
            self.tgi_fridays.login()

        assert len(responses.calls._calls) == 1
