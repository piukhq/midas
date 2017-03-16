import unittest
import xmltodict
import os
from os.path import join
from cron_test_results import parse_test_results, generate_message, post_formatted_slack_message


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

    def test_generate_message_filter_by_cause(self):
        bad_agents = [
            {'classname': 'test_captcha_1', 'name': 'avis',
             'cause': 'LoginError: Tripped captcha: The agent has tripped the scheme capture code'},
            {'classname': 'test_captcha_2', 'name': 'choicehotels',
             'cause': 'LoginError: Tripped captcha: The agent has tripped the scheme.'},
            {'classname': 'test_failure_1', 'name': 'monsoon',
             'cause': 'TypeError: NoneType object is not subscriptable'},
            {'classname': 'test_failure_2', 'name': 'hyatt', 'cause': 'AssertionError: LoginError not raised'},
            {'classname': 'test_failure_3', 'name': 'rewards4golf',
             'cause': 'Exception: missing the credential ctl00$txtUsername.'},
            {'classname': 'test_credentials_1', 'name': 'accor',
             'cause': 'LoginError: Invalid credentials: We could not upda'},
        ]

        with open(join(os.path.dirname(os.path.abspath(__file__)), 'fixtures/example_test_results.xml')) as f:
            test_results = xmltodict.parse(f.read())

        message = generate_message(test_results, bad_agents)

        self.assertEqual(len(message['failures']), 3, msg="Should filter 3 messages as failures.")
        self.assertEqual(len(message['captcha']), 2, msg="Should filter 2 messages as captcha.")
        self.assertEqual(len(message['credentials']), 1, msg="Should filter 3 messages as credentials.")
        self.assertEquals(message['error_info'], '*Total errors:* 17/234\n*Time:* 128.817 seconds\n')
        self.assertEquals(message['end_site_down'], 'thai airways, harrods')
