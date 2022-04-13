import datetime
import time
import unittest

import arrow

from app.agents.exceptions import AgentError
from app.security.base import BaseSecurity


class TestBaseSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.base_security = BaseSecurity()

    def test_validate_timestamp(self):
        with self.assertRaises(AgentError) as e:
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
