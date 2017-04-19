import os
import unittest
import xmltodict

from cron_test_results import generate_message, get_problematic_agents


class TestCronResults(unittest.TestCase):

    TEST_RESULT_FILE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'fixtures',
        'example_test_results.xml'
    )

    def test_get_problematic_agents(self):
        expected_bad_agents = [
            {
                'classname': 'test_boots',
                'name': 'boots',
                'cause': 'LoginError: An unknown error has occurred: We have no idea what went wrong the team is '
                         'on to it. code: 520...'
            },
            {
                'classname': 'test_foyles_bookstore',
                'name': 'foyles bookstore',
                'cause': 'LoginError: Invalid credentials: We could not update your account because your username '
                         'and/or password were reported to be inco...'
            },
            {
                'cause': 'AgentError: End site down: The scheme end site is currently down. code: 530...',
                'classname': 'test_harrods',
                'name': 'harrods'
            },
            {
                'cause': 'LoginError: Tripped captcha: The agent has tripped the scheme capture code: 532...',
                'classname': 'test_nandos',
                'name': 'nandos'
            },
            {
                'classname': 'test_starwood',
                'name': 'starwood',
                'cause': 'LoginError: Account locked on end site: We could not update your account because it '
                         'appears your account has been locked. This u...'
            },
            {
                'cause': 'AgentError: End site down: The scheme end site is currently down. code: 530...',
                'classname': 'test_thai_airways',
                'name': 'thai airways'},
            {
                'cause': 'selenium.common.exceptions.WebDriverException: Message: Can not '
                         "connect to the 'chromedriver'...",
                'classname': 'test_starbucks',
                'name': 'starbucks'
            }
        ]

        with open(self.TEST_RESULT_FILE_PATH) as f:
            test_results = xmltodict.parse(f.read())

        bad_agents = get_problematic_agents(test_results)

        self.assertEqual(
            len(bad_agents),
            len(expected_bad_agents)
        )
        self.assertEqual(
            sorted(bad_agents, key=lambda k: k['name']),
            sorted(expected_bad_agents, key=lambda k: k['name'])
        )

    def test_generate_message_filter_by_cause(self):
        bad_agents = [
            {'classname': 'test_captcha_1', 'name': 'avis',
             'cause': 'LoginError: Tripped captcha: The agent has tripped the scheme capture code'},
            {'classname': 'test_captcha_2', 'name': 'choicehotels',
             'cause': 'LoginError: Tripped captcha: The agent has tripped the scheme.'},
            {'classname': 'test_failure_1', 'name': 'monsoon',
             'cause': 'TypeError: NoneType object is not subscriptable'},
            {'classname': 'test_failure_2', 'name': 'hyatt', 'cause': 'AssertionError: LoginError not raised'},
            {'classname': 'test_credentials_1', 'name': 'rewards4golf',
             'cause': 'Exception: missing the credential ctl00$txtUsername.'},
            {'classname': 'test_credentials_2', 'name': 'accor',
             'cause': 'LoginError: Invalid credentials: We could not upda'},
        ]

        with open(self.TEST_RESULT_FILE_PATH) as f:
            test_results = xmltodict.parse(f.read())

        message = generate_message(test_results, bad_agents)

        self.assertEqual(len(message['failures']), 2, msg="Should filter 3 messages as failures.")
        self.assertEqual(len(message['captcha']), 2, msg="Should filter 2 messages as captcha.")
        self.assertEqual(len(message['credentials']), 2, msg="Should filter 3 messages as credentials.")
        self.assertEquals(message['error_info'], '*Total errors:* 17/234\n*Time:* 128.817 seconds\n')
        self.assertEquals(message['end_site_down'], 'thai airways, harrods')
