import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import parse_test_results, generate_message


class TestCronResults(unittest.TestCase):
    def test_parse_test_results(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        failures = parse_test_results(test_results)
        self.assertIsInstance(failures, dict)
        self.assertIn('test_nandos', failures)
        self.assertEqual(len(failures['test_nandos']), 2)
        self.assertEqual(failures['test_nandos']['cause'],
                         'LoginError: Tripped captcha: The agent has tripped the scheme capture code: 532...')
        self.assertEqual(failures['test_nandos']['count'], 4)

    def test_generate_message(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())

        bad_agents = [
            {'name': 'test1', 'cause': 'test2'},
            {'name': 'test3', 'cause': 'test4'},
        ]

        message = generate_message(test_results, bad_agents)

        expected_message = '''*Total errors:* 17/234
*Time:* 128.817 seconds

*Errors*
>test1 - test2
>test3 - test4

*Warnings*
>_There are currently no notable agent warnings._

*End site down:* harrods, thai airways
http://dev.apollo.loyaltyangels.local/#/exceptions/'''

        self.assertEqual(expected_message, message)
