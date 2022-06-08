import json
import unittest

import httpretty
from soteria.configuration import Configuration

from app.exceptions import ConfigurationError, ServiceConnectionError
from app.security.oauth import OAuth


class TestOauth(unittest.TestCase):
    def setUp(self) -> None:
        self.token_url = "https://reflector.dev.gb.bink.com/mock/oauth2/token/"
        self.oauth = OAuth()
        self.credentials_missing = {"outbound": {"service": Configuration.OAUTH_SECURITY, "credentials": []}}
        self.oauth.credentials = {
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [
                    {
                        "credential_type": "compound_key",
                        "storage_key": "a_storage_key",
                        "value": {
                            "payload": {
                                "client_id": "a_client_id",
                                "client_secret": "a_client_secret",
                                "grant_type": "client_credentials",
                                "resource": "a_resource",
                            },
                            "prefix": "Bearer",
                            "url": self.token_url,
                        },
                    }
                ],
            }
        }
        self.expected_success_resp = {"headers": {"Authorization": "Bearer a_token"}, "json": {"key": "value"}}

    @httpretty.activate
    def test_encode(self):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.token_url,
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=200)],
        )
        resp = self.oauth.encode(json.dumps({"key": "value"}))
        self.assertEqual(self.expected_success_resp, resp)

    @httpretty.activate
    def test_encode_on_request_failure(self):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.token_url,
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=500)],
        )
        with self.assertRaises(ServiceConnectionError) as e:
            self.oauth.encode(json.dumps({"key": "value"}))
        self.assertEqual(e.exception.name, "Service connection error")

    @httpretty.activate
    def test_encode_on_request_key_error_failure(self):
        httpretty.register_uri(
            httpretty.POST,
            uri=self.token_url,
            responses=[httpretty.Response(body=json.dumps({"access_token": "a_token"}), status=200)],
        )
        self.oauth.credentials = self.credentials_missing
        with self.assertRaises(ConfigurationError) as e:
            self.oauth.encode(json.dumps({"key": "value"}))
        self.assertEqual(e.exception.name, "Configuration error")
