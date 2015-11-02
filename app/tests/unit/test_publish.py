import unittest
from unittest.mock import patch
from app.publish import transactions, balance



class TestRetry(unittest.TestCase):
    @patch('app.publish.post', autospec=True)
    def test_transactions(self, mock_post):
        items = transactions([{}, ], 5)
        self.assertEqual(items, [{'scheme_account_id': 5}])
        self.assertTrue(mock_post.called)
        self.assertTrue(mock_post.call_args[0][0][-13:], '/transactions')

    @patch('app.publish.post', autospec=True)
    def test_balance(self, mock_post):
        item = balance({}, 5, 8)
        self.assertEqual(item, {'user_id': 8, 'scheme_account_id': 5})
        self.assertTrue(mock_post.called)


