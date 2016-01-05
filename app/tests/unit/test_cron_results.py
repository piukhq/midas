import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import generate_message


class TestCronResults(unittest.TestCase):
    def test_generate_message(self):
        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())
        message = generate_message(test_results)
        self.assertTrue(message.startswith("*Total errors:* 17"))
        self.assertIn('Nandos', message)
        self.assertIn('Starbucks', message)
        self.assertIn('*End site down:*', message)
