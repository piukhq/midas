import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import parse_test_results
from collections import defaultdict


class TestCronResults(unittest.TestCase):
    def test_parse_test_results(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        failures = parse_test_results(test_results)
        self.assertIsInstance(failures, defaultdict)
        self.assertIn('nandos', failures)
        self.assertEqual(len(failures['nandos']), 4)
        self.assertEqual(failures['nandos'][0], 'test balance')
