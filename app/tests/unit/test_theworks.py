import json
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock, Mock, call, patch

import httpretty
from flask_testing import TestCase
from soteria.configuration import Configuration

import settings
from app.agents.theworks import TheWorks
from app.api import create_app
from app.exceptions import AccountAlreadyExistsError, CardNumberError, JoinError, ResourceNotFoundError
from app.scheme_account import JourneyTypes

settings.API_AUTH_ENABLED = False

OUTBOUND_SECURITY_CREDENTIALS = {
    "outbound": {
        "service": Configuration.OPEN_AUTH_SECURITY,
        "credentials": [
            {
                "value": {
                    "user_id": "1234",
                    "password": "pass",
                },
            }
        ],
    },
}

CREDENTIALS = {
    "first_name": "Fake",
    "last_name": "Name",
    "email": "email@domain.com",
    "consents": [{"id": 11738, "slug": "email_marketing", "value": False, "created_on": "1996-09-26T00:00:00"}],
}

RESPONSE_JSON_200 = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": [
        "nonsense",
        "0",
        "12809967",
        "Michal",
        "Jozwiak",
        "2023-05-03",
        "603628452152593745761",
        "",
        "",
        "",
        "",
        "",
        "",
    ],
}


class TestTheWorksJoin(TestCase):
    def create_app(self):
        return create_app(self)

    def setUp(self):
        self.outbound_security_credentials = OUTBOUND_SECURITY_CREDENTIALS
        self.credentials = CREDENTIALS

        with (
            mock.patch("app.agents.base.Configuration") as mock_configuration,
            mock.patch("app.agents.theworks.get_task") as mock_get_task,
        ):
            mock_get_task.return_value = Mock(attempts=0)
            mock_config_object = MagicMock()
            mock_config_object.security_credentials = self.outbound_security_credentials
            mock_config_object.integration_service = "SYNC"
            mock_configuration.return_value = mock_config_object
            self.the_works = TheWorks(
                retry_count=1,
                user_info={
                    "user_set": "27558",
                    "credentials": self.credentials,
                    "status": 442,
                    "journey_type": JourneyTypes.JOIN,
                    "scheme_account_id": 94532,
                    "channel": "com.bink.wallet",
                },
                scheme_slug="the-works",
            )
            self.the_works.base_url = "https://fake.url/"
            self.the_works.max_retries = 0

    @mock.patch("app.agents.theworks.uuid.uuid4", return_value="uid")
    def test_join_payload_with_join_vars(self, mock_uid):
        self.the_works.credentials = {
            "first_name": "Fake",
            "last_name": "Name",
            "email": "email@domain.com",
            "consents": [{"id": 11738, "slug": "email_marketing", "value": True, "created_on": "1996-09-26T00:00:00"}],
        }
        payload = self.the_works._join_payload()
        expected = {
            "jsonrpc": "2.0",
            "method": "dc_946",  # request method
            "id": 1,
            "params": [
                "en",  # language code
                "uid",  # transaction code
                "1234",  # user id
                "pass",  # password
                "",  # givex number
                "CUSTOMER",  # customer type
                "email@domain.com",  # customer login
                "",  # customer title
                "Fake",  # customer first name
                "",  # customer middle name
                "Name",  # customer last name
                "",  # customer gender
                "",  # customer birthday
                "",  # customer address
                "",  # customer address 2
                "",  # customer city
                "",  # customer province
                "",  # customer county
                "",  # customer country
                "",  # postal code
                "",  # phone number
                "0",  # customer discount
                "t",  # promotion optin
                "email@domain.com",  # customer email
                "uid",  # customer password
                "",  # customer mobile
                "",  # customer company
                "",  # security code
                "t",  # new card request
            ],
        }

        self.assertEqual(payload, expected)

    @mock.patch("app.agents.theworks.uuid.uuid4", return_value="uid")
    def test_join_payload_with_register_vars(self, mock_uid):
        self.the_works.credentials = {
            "first_name": "Fake",
            "last_name": "Name",
            "email": "email@domain.com",
            "card_number": "5556",
            "consents": [{"id": 11738, "slug": "email_marketing", "value": False, "created_on": "1996-09-26T00:00:00"}],
        }
        payload = self.the_works._join_payload()
        expected = {
            "jsonrpc": "2.0",
            "method": "dc_946",  # request method
            "id": 1,
            "params": [
                "en",  # language code
                "uid",  # transaction code
                "1234",  # user id
                "pass",  # password
                "5556",  # givex number
                "CUSTOMER",  # customer type
                "email@domain.com",  # customer login
                "",  # customer title
                "Fake",  # customer first name
                "",  # customer middle name
                "Name",  # customer last name
                "",  # customer gender
                "",  # customer birthday
                "",  # customer address
                "",  # customer address 2
                "",  # customer city
                "",  # customer province
                "",  # customer county
                "",  # customer country
                "",  # postal code
                "",  # phone number
                "0",  # customer discount
                "f",  # promotion optin
                "email@domain.com",  # customer email
                "uid",  # customer password
                "",  # customer mobile
                "",  # customer company
                "",  # security code
                "f",  # new card request
            ],
        }

        self.assertEqual(payload, expected)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.theworks.signal", autospec=True)
    def test_create_account_200(self, mock_signal, mock_requests_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(RESPONSE_JSON_200),
                    status=HTTPStatus.OK,
                )
            ],
        )
        expected_calls = [  # The expected call stack for signal, in order
            call("join-success"),
            call().send(self.the_works, channel=self.the_works.channel, slug=self.the_works.scheme_slug),
        ]
        self.the_works.join()
        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(self.the_works.credentials["card_number"], RESPONSE_JSON_200["result"][6])

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.theworks.signal", autospec=True)
    def test_join_account_exists(self, mock_signal, mock_requests_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"jsonrpc": "2.0", "id": 1, "result": ["1234", "182", "Account already exists"]}),
                    status=200,
                )
            ],
        )

        with self.assertRaises(AccountAlreadyExistsError) as e:
            expected_calls = [  # The expected call stack for signal, in order
                call("join-fail"),
                call().send(self.the_works, channel=self.the_works.channel, slug=self.the_works.scheme_slug),
            ]
            self.the_works.join()
        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "Account already exists")
        self.assertEqual(e.exception.code, 445)

        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps(
                        {"jsonrpc": "2.0", "id": 1, "result": ["1234", "67", "This member is already enrolled"]}
                    ),
                    status=200,
                )
            ],
        )

        with self.assertRaises(AccountAlreadyExistsError) as e:
            expected_calls = [  # The expected call stack for signal, in order
                call("join-fail"),
                call().send(self.the_works, channel=self.the_works.channel, slug=self.the_works.scheme_slug),
            ]
            self.the_works.join()
        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "Account already exists")
        self.assertEqual(e.exception.code, 445)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.theworks.signal", autospec=True)
    def test_join_unknown_error(self, mock_signal, mock_requests_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"jsonrpc": "2.0", "id": 1, "result": ["1234", "19", "Operation not permitted"]}),
                    status=200,
                )
            ],
        )

        with self.assertRaises(JoinError) as e:
            expected_calls = [  # The expected call stack for signal, in order
                call("join-fail"),
                call().send(self.the_works, channel=self.the_works.channel, slug=self.the_works.scheme_slug),
            ]
            self.the_works.join()

        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "General error preventing join")
        self.assertEqual(e.exception.code, 538)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    @mock.patch("app.agents.theworks.signal", autospec=True)
    def test_join_cardnumber_error(self, mock_signal, mock_requests_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body=json.dumps({"jsonrpc": "2.0", "id": 1, "result": ["1234", "2", "Cert not exist"]}),
                    status=200,
                )
            ],
        )

        with self.assertRaises(CardNumberError) as e:
            expected_calls = [  # The expected call stack for signal, in order
                call("join-fail"),
                call().send(self.the_works, channel=self.the_works.channel, slug=self.the_works.scheme_slug),
            ]
            self.the_works.join()

        mock_signal.assert_has_calls(expected_calls)
        self.assertEqual(e.exception.name, "Card not registered or Unknown")
        self.assertEqual(e.exception.code, 436)

    @httpretty.activate
    @mock.patch("requests.Session.post", autospec=True)
    def test_join_notfound_error(self, mock_requests_session):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.the_works.base_url,
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(
                    body="Resource not found",
                    status=404,
                )
            ],
        )

        with self.assertRaises(ResourceNotFoundError) as e:
            self.the_works.join()

        self.assertEqual(e.exception.name, "Resource not found")
        self.assertEqual(e.exception.code, 530)
