import unittest
from unittest.mock import patch
from app.retry import get_key, inc_count, get_count



class TestRetry(unittest.TestCase):
    def test_get_key(self):
        self.assertEqual(get_key("tesco", 'bob'), "retry-tesco-bob")

    @patch('app.retry.redis')
    def test_inc_count_exists(self, mock_redis):
        inc_count("345", 0, True)
        self.assertEqual(mock_redis.set.call_args[0], ('345', 1))
        self.assertFalse(mock_redis.expire.called)

    @patch('app.retry.redis')
    def test_inc_count(self, mock_redis):
        inc_count("345", 4, False)
        self.assertEqual(mock_redis.set.call_args[0], ('345', 5))
        self.assertEqual(mock_redis.expire.call_args[0], ('345', 60*15))

    @patch('app.retry.redis')
    def test_get_count(self, mock_redis):
        mock_redis.get.return_value = None
        exists, retry_count = get_count("345")

        self.assertFalse(exists)
        self.assertTrue(mock_redis.get.called)
        self.assertEqual(retry_count, 0)

    @patch('app.retry.redis')
    def test_max_out_count(self, mock_redis):
        self.assertTrue(mock_redis.get.set)
        self.assertTrue(mock_redis.get.expire)

    @patch('app.retry.redis')
    def test_get_count_exists(self, mock_redis):
        mock_redis.get.return_value = '1'
        exists, retry_count = get_count("345")

        self.assertTrue(exists)
        self.assertTrue(mock_redis.get.called)
        self.assertEqual(retry_count, 1)