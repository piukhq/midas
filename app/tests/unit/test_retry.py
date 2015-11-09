import unittest
from unittest.mock import patch
from app.retry import get_key, inc_count, get_count


class TestRetry(unittest.TestCase):
    def test_get_key(self):
        self.assertEqual(get_key("tesco", 'bob'), "retry-tesco-bob")

    @patch('app.retry.redis')
    def test_inc_count(self, mock_redis):
        inc_count("345")
        self.assertEqual(mock_redis.incr.call_args[0][0], '345')

    @patch('app.retry.redis')
    def test_get_count(self, mock_redis):
        mock_redis.get.return_value = None
        retry_count = get_count("345")

        self.assertTrue(mock_redis.get.called)
        self.assertEqual(retry_count, 0)

    @patch('app.retry.redis')
    def test_max_out_count(self, mock_redis):
        self.assertTrue(mock_redis.get.set)
        self.assertTrue(mock_redis.get.expire)
