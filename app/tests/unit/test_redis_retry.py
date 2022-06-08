import unittest
from unittest.mock import patch

import redis

from app.exceptions import ServiceConnectionError
from app.redis_retry import get_count, get_key, inc_count, redis_connection


class TestRedisRetry(unittest.TestCase):
    def test_get_key(self):
        self.assertEqual(get_key("tesco", "bob"), "retry-tesco-bob")

    @patch("app.redis_retry.redis")
    def test_inc_count(self, mock_redis):
        inc_count("345")
        self.assertEqual(mock_redis.incr.call_args[0][0], "345")

    @patch("app.redis_retry.redis")
    def test_get_count(self, mock_redis):
        mock_redis.get.return_value = None
        retry_count = get_count("345")

        self.assertTrue(mock_redis.get.called)
        self.assertEqual(retry_count, 0)

    @patch("app.redis_retry.redis")
    def test_max_out_count(self, mock_redis):
        self.assertTrue(mock_redis.get.set)
        self.assertTrue(mock_redis.get.expire)

    def test_redis_connection_decorator_handles_connection_error(self):
        @redis_connection
        def func():
            raise redis.exceptions.ConnectionError("Test connection error")

        with self.assertRaises(ServiceConnectionError) as e:
            func()

        self.assertEqual(e.exception.message, "Error connecting to Redis.")
