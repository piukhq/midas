import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import generate_message, format_table, parse_test_results
from collections import defaultdict


class TestCronResults(unittest.TestCase):
    def test_generate_message(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        message = generate_message(test_results)
        self.assertTrue(message.startswith("*Total errors:* 17"))
        self.assertIn('Nandos', message)
        self.assertIn('Starbucks', message)
        self.assertIn('*End site down:*', message)

    def test_parse_test_results(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        failures = parse_test_results(test_results)
        self.assertIsInstance(failures, defaultdict)
        self.assertIn('nandos', failures)
        self.assertEqual(len(failures['nandos']), 4)
        self.assertEqual(failures['nandos'][0], 'test balance')

    def test_format_table(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        failures = parse_test_results(test_results)
        table = format_table(failures)
        self.assertIn('Nandos', table)
        self.assertIn('Starbucks', table)
