import unittest
from decimal import Decimal
from unittest.mock import patch
from app.publish import transactions, balance, zero_balance


class TestRetry(unittest.TestCase):
    @patch('app.publish.post', autospec=True)
    def test_transactions(self, mock_post):
        items = transactions([{}, ], 5, 3, '123-12')
        self.assertEqual(items, [{'scheme_account_id': 5, 'user_id': 3}])
        self.assertTrue(mock_post.called)
        self.assertTrue(mock_post.call_args[0][0][-13:], '/transactions')

    @patch('app.publish.post', autospec=True)
    def test_balance(self, mock_post):
        b = {
            'points': Decimal('51251285'),
            'value': Decimal('9.44'),
            'value_label': '£9.44',
        }
        item = balance(b, 5, 8, '123-12')
        self.assertEqual(item, {
            'user_set': 8,
            'value': Decimal('9.44'),
            'scheme_account_id': 5,
            'points': Decimal('51251285'),
            'value_label': '£9.44',
            'points_label': '51M',
            'reward_tier': 0
        })
        self.assertTrue(mock_post.called)

    def test_transactions_none(self):
        self.assertIsNone(transactions(None, 5, 2, '123-12'))

    @patch('app.publish.post', autospec=True)
    def test_balance_long_value_label(self, mock_post):
        b = {
            'points': Decimal('0'),
            'value': Decimal('0'),
            'value_label': 'this is far too long...'
        }
        item = balance(b, 5, 8, '123-12')

        self.assertEqual(item['value_label'], 'Reward')

    @patch('app.publish.post', autospec=True)
    def test_zero_balance(self, mock_post):
        item = zero_balance(5, 8, '123-12')
        self.assertEqual(item, {
            'user_set': 8,
            'value': Decimal('0'),
            'scheme_account_id': 5,
            'points': Decimal('0'),
            'value_label': 'Pending',
            'points_label': '0',
            'reward_tier': 0
        })
        self.assertTrue(mock_post.called)
