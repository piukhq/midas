import unittest
from decimal import Decimal
from unittest.mock import patch
from app.publish import transactions, balance, zero_balance, create_balance_object, PENDING_BALANCE

expected_balance = {
    'scheme_account_id': 1,
    'user_id': 2,
    'points_label': '1',
    'points': Decimal(1.1),
    'value': Decimal(2.2),
}


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
            'user_id': 8,
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
            'user_id': 8,
            'value': Decimal('0'),
            'scheme_account_id': 5,
            'points': Decimal('0'),
            'value_label': 'Pending',
            'points_label': '0',
            'reward_tier': 0
        })
        self.assertTrue(mock_post.called)

    def test_create_balance_object(self):
        agent_balance = {
            'points': Decimal(1.1),
            'value': Decimal(2.2),
            'value_label': 'points',
            'reward_tier': 5
        }
        b = create_balance_object(agent_balance, 1, 2)

        expected_balance['value_label'] = 'points'
        expected_balance['reward_tier'] = 5
        self.assertEqual(b, expected_balance)

    def test_create_balance_object_without_reward_tier(self):
        b = create_balance_object(PENDING_BALANCE, 1, 2)

        self.assertEqual(b['reward_tier'], 0)

    def test_create_balance_object_with_max_label(self):
        agent_balance = {
            'points': Decimal(1.1),
            'value': Decimal(2.2),
            'value_label': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'reward_tier': 5
        }
        b = create_balance_object(agent_balance, 1, 2)

        self.assertEqual(b['value_label'], 'Reward')
