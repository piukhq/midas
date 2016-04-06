import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import parse_test_results


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
