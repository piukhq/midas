import datetime
import json
import time
import unittest
from unittest import mock

import arrow
from soteria.configuration import Configuration

from app.exceptions import ConfigurationError, UnknownError, ValidationError
from app.security.base import BaseSecurity
from app.security.open_auth import OpenAuth
from app.security.rsa import RSA
from app.security.utils import authorise, get_security_agent

PRIVATE_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEpAIBAAKCAQEAsw2VXAHRqPaCDVYI6Lug3Uq9Quik7m3sI8BkzqdCkBmakPZ5\n"
    "cssbc4EsxETTA9V0V1KDMUy6vGUSaN8pbg4MPDZOzUlJyOcBAhaKWpUH4Bw0OlBt\n"
    "KPVewN51n8NZHvwqh39f5rwVNVB5T2haTOsuG0Q7roH5TPYs75F87bELwRLCnWyX\n"
    "o69f6o6fH7N+M2CN11S1UKT7ZkqaL2fm3LWuf8GWAkOrvrZp6js3kKCCuztI+JxP\n"
    "93Aa3411aVH1jt0Wgyex+ekdAO2ykGq2tbs9vGi//6ZweZey+B1+2LrCum1+Wula\n"
    "f1lGLNF5Bo6fHuXXw63fhx54PQe8pMWc5LW93wIDAQABAoIBAQCEdnQc0SuueE/W\n"
    "VePZaZWkoPpLWZlK2v9ro5XwXEUeHhL/U5idmC0C0nmv6crCd1POljiAbGdpoMxx\n"
    "0UbxKGtc0ECUFrgDbQKN7OcGBGMDJVpuGbnoJz6mKO2T+A0ioyNDgrQMGvEFtDdK\n"
    "y8SiSwqdGWmdvIIWsbiks1lc7zHm7yAUWSp/XYgsw73+xsU+3wRlrEGsUoiTlb5J\n"
    "ZAGXBd95Gix7FQeX04WDP47xtdaydz2G/dhqsN8w78peMDPMNd/LPKMpAHYCT/5b\n"
    "wri0nfzVjNMHULCZU4KoopO8De0M1aik5GwWOdnFx6z/VkW/drXltfc9MKOJKXP7\n"
    "WI5wSCHhAoGBAOmt8z7y5RYuhIum8+e1hsQPb0ah55xcGSK8Vb066xx1XFxlgWB+\n"
    "Xiv+Ga7nQvJm3johLPuIFp0eQKrJ3a+KH+L6biM20S7K5hfxi3qdrHOBd8qKoRWS\n"
    "cbR1V40TYxXTvWYYUa2jnKPsB0msm+3l0jwNLZhygbhwDtw1cNhed2ebAoGBAMQn\n"
    "4UPHU1HE7nUI09eY11eUURuB69TRIoZNO3VVII83RHro7qHyKWk0W2RevjrE8ir2\n"
    "S4ivFYQU5lca6QmcsPj7iGtFbeVImuTWwDTaahCFcfV/pV0L6xxU/7TowKivABHe\n"
    "SUVwZJU+sPPcSSHZRa1uP7/6XD5oZEnysm1Vx6ENAoGBAKQiw/XWRKVE/WLeXPnH\n"
    "Hqb+NGoHdRj1883bPdoR1W0C3mIkBjER8fGypLWeyP5c1QE9pkvzNfccdc3Axw7y\n"
    "1RzoTI49hcb5S49L4W257JShPtQsdaMiXu2jcmCsWm/Nb36T3GM7xd25/xB3xnre\n"
    "b8Iwe3NWEtnLFBUHEIFaMUK7AoGAHoqHDGKQmn6rEhXZxgvKG5zANCQ6b9xQH9EO\n"
    "nOowM5xLUUfLP/PQdszsHeiSfdwESKQohpOcKgCHDLDn79MxytJ/HxSkU7rGQzMc\n"
    "oh4PvZrJb4v8V0xvwu2JEsXamWkF/cI6blFdl883BgEacea+bo5n5qA4lI70bn8X\n"
    "QObGOlECgYAURWOAKLd7RzgNrBorqof4ZZxdNXgOGq9jb4FE+bWI48EvTVGBmt7u\n"
    "9pHA57UX0Nf1UQ/i3dKAvm5GICDUuWHvUnnb3m+pbx0w91YSXR9t8TVNdJ2dMhNu\n"
    "ZSEUFQWbkQLUGtorzjqGssXHxKVa+9riPpztJNDl+8oHhu28wu4WyQ==\n"
    "-----END RSA PRIVATE KEY-----\n"
)

PUBLIC_KEY = (
    "-----BEGIN RSA PUBLIC KEY-----\n"
    "MIIBCgKCAQEAsw2VXAHRqPaCDVYI6Lug3Uq9Quik7m3sI8BkzqdCkBmakPZ5cssb\n"
    "c4EsxETTA9V0V1KDMUy6vGUSaN8pbg4MPDZOzUlJyOcBAhaKWpUH4Bw0OlBtKPVe\n"
    "wN51n8NZHvwqh39f5rwVNVB5T2haTOsuG0Q7roH5TPYs75F87bELwRLCnWyXo69f\n"
    "6o6fH7N+M2CN11S1UKT7ZkqaL2fm3LWuf8GWAkOrvrZp6js3kKCCuztI+JxP93Aa\n"
    "3411aVH1jt0Wgyex+ekdAO2ykGq2tbs9vGi//6ZweZey+B1+2LrCum1+Wulaf1lG\n"
    "LNF5Bo6fHuXXw63fhx54PQe8pMWc5LW93wIDAQAB\n"
    "-----END RSA PUBLIC KEY-----\n"
)

ENCODED_JSON = {
    "headers": {
        "Authorization": "Signature"
        "pVHkBohc4zbcqoIpjRnIa4M/xq95/L+tbznvALzhHXCeVD5fvwB9W+ZJTEI3frMkgauxM5EajGhVK+U5QGuVbj1cA9i/hQ0XAlx51O04yHIktQtkzhB4bUbEJziLMsbfwo9/aRAJk8lfmHUo3BB5P93aB/ziWmplaB4/TskC8ru7+ulkyyRAtCJ3I3+IyXgbtO0kgf5i+E+u+GWq38qu2tRP8/SUNVIhVhXt2mtT51NR3sORuJpZuIqnv0bF44kByFp13sL9Y/X/jXbe0wC9KJ1vfhC9G/2VJqc8XHnipsa8Z0SWwktMH9+PtlFuNBvMdG3FE9YJ0H5RgKd2q1ty0A==",  # noqa
        "X-REQ-TIMESTAMP": 1665748627,
    },
    "json": {"abc": "123"},
}


class TestUtils(unittest.TestCase):
    @mock.patch("app.security.utils.import_module", side_effect=ImportError)
    def test_get_security_agent_raises_config_error_when_import_error(self, mock_import_module):
        with self.assertRaises(ConfigurationError):
            get_security_agent(Configuration.RSA_SECURITY)

    @mock.patch("app.security.utils.import_module", side_effect=AttributeError)
    def test_get_security_agent_raises_config_error_when_attribute_error(self, mock_import_module):
        with self.assertRaises(ConfigurationError):
            get_security_agent(Configuration.RSA_SECURITY)

    def test_authorise_throws_unknown_error(self):
        @authorise(0)
        def some_function():
            pass

        with self.assertRaises(UnknownError):
            some_function()


class TestOpenAuth(unittest.TestCase):
    def setUp(self) -> None:
        self.open_auth = OpenAuth()

    def test_encode(self):
        self.assertEqual(self.open_auth.encode(json.dumps({"key": "value"})), {"json": {"key": "value"}})

    def test_decode(self):
        self.assertEqual(self.open_auth.decode("123", {"key": "value"}), {"key": "value"})

    def test_decode_no_data(self):
        self.assertEqual(self.open_auth.decode("", {}), "{}")


class TestRSA(unittest.TestCase):
    def setUp(self) -> None:
        self.rsa = RSA()
        self.rsa.credentials = {
            "outbound": {
                "service": 2,
                "credentials": [
                    {
                        "credential_type": "bink_private_key",
                        "storage_key": "a_storage_key",
                        "value": PRIVATE_KEY,
                    }
                ],
            },
            "inbound": {
                "service": 2,
                "credentials": [
                    {
                        "credential_type": "merchant_public_key",
                        "storage_key": "a_storage_key",
                        "value": PUBLIC_KEY,
                    }
                ],
            },
        }

    def test_encode(self):
        self.assertEqual(self.rsa.encode(json.dumps({"abc": "123"}))["json"], ENCODED_JSON["json"])

    def test_decode_invalid_signature_raises_validation_error(self):
        encoded = self.rsa.encode(json.dumps({"abc": "123"}))
        with self.assertRaises(ValidationError):
            self.rsa.decode(encoded["headers"], "123")

    def test_decode(self):
        json_data = json.dumps({"abc": "123"})
        signed = self.rsa.encode(json_data)

        decoded_json = self.rsa.decode(signed["headers"], json_data)

        self.assertEqual(decoded_json, json_data)


class TestBaseSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.base_security = BaseSecurity()

    def test_validate_timestamp(self):
        with self.assertRaises(ValidationError) as e:
            self.base_security._validate_timestamp(arrow.get(datetime.date(1996, 5, 5)).int_timestamp)
        self.assertEqual(e.exception.name, "Failed validation")

    def test_add_timestamp(self):
        json_data = {"key": "value"}
        json_with_timestamp, current_time = self.base_security._add_timestamp(json_data)
        self.assertEqual(int(time.time()), current_time)
        self.assertEqual("{}{}".format(json_data, current_time), json_with_timestamp)

    def test_get_key(self):
        credentials_list = [{"credential_type": "some_type", "value": "key-123"}]
        key = self.base_security._get_key("some_type", credentials_list)
        self.assertEqual(key, "key-123")
        credentials_list.pop(0)
        with self.assertRaises(KeyError) as e:
            key = self.base_security._get_key("some_type", credentials_list)
        self.assertEqual(e.exception.args[0], "some_type not in credentials")

    def test_get_nonexistent_key_raises_key_error(self):
        credentials_list = [
            {
                "credential_type": "compound_key",
                "storage_key": "a_storage_key",
                "value": {"password": "paSSword", "username": "username@bink.com"},
            }
        ]
        credential_value = self.base_security._get_key("compound_key", credentials_list)
        self.assertEqual(credential_value, credentials_list[0]["value"])
