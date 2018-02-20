#!/usr/bin/env python3
"""
This script is to run as a cron to provide the junit xml for the apollo service to view
"""

import os
import re
import subprocess
import sys
from os.path import join

import requests
import xmltodict
from influxdb import InfluxDBClient
from slacker import Slacker

from app.active import AGENTS
from app.tests.service.logins import update_credentials
from settings import SLACK_API_KEY, HELIOS_URL, JUNIT_XML_FILENAME, INFLUX_HOST, INFLUX_PORT, INFLUX_USER, \
    INFLUX_PASSWORD, INFLUX_DATABASE, HEARTBEAT_URL

test_path = 'app/tests/service/'
parallel_processes = 4

influx = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, INFLUX_USER, INFLUX_PASSWORD, INFLUX_DATABASE)

# the number of hours of failure considered to be problematic for an agent
PROBLEMATICAL_THRESHOLD = 6

# regexes that can help pull error causes out of test errors and failures.
# these are ordered from most to least helpful. if the most helpful one fails, the next is tried, and so on.
error_cause_regexes = [
    re.compile(r'^E.*?app\.agents\.exceptions\.(.*?)$', re.MULTILINE),
    re.compile(r'^E\s*-\s*(.*)$', re.MULTILINE),
    re.compile(r'^E\s*(.*)$', re.MULTILINE),
]


def post_formatted_slack_message(message, channel='#errors-agents'):
    Slacker(SLACK_API_KEY).chat.post_message(
        channel,
        text=message['error_info'],
        attachments=[
            {
                "color": "#F90400",
                "title": "Errors",
                "title_link": "{0}/#/exceptions/".format(HELIOS_URL),
                "fields": [{"value": i} for i in message['failures']]
            },
            {
                "color": "#ADE0FF",
                "title": "Login Failures",
                "title_link": "{0}/#/exceptions/".format(HELIOS_URL),
                "fields": [{"value": i} for i in message['credentials']]
            },
            {
                "color": "#ADE0FF",
                "title": "The Unscrapables",
                "title_link": "{0}/#/exceptions/".format(HELIOS_URL),
                "fields": [{"value": i} for i in message['captcha']]
            },
            {
                "color": "#C9C9CF",
                "title": "End site down",
                "text": message['end_site_down'],

            }
        ]
    )


def is_flagged(agent, flags):
    return any(flag in agent['cause'].lower() for flag in flags)


def generate_failures_and_warnings(bad_agents):
    failures = []
    captcha = []
    credentials = []

    captcha_flags = [
        'captcha',
        'ip blocked',
    ]

    credential_flags = [
        'invalid credentials',
        'missing the credential'
    ]

    # makes sure end site down errors are not considered again
    ignored_flags = [
        'end site down',
    ]

    for agent in bad_agents:
        if is_flagged(agent, captcha_flags):
            captcha.append('{0} - {1}'.format(agent['name'], agent['cause']))
        elif is_flagged(agent, credential_flags):
            credentials.append('{0} - {1}'.format(agent['name'], agent['cause']))
        else:
            failures.append('{0} - {1}'.format(agent['name'], agent['cause']))
        # takes out all the errors that should be ignored
        for ignored_flag in ignored_flags:
            if ignored_flag in agent['cause'].lower():
                if '{0} - {1}'.format(agent['name'], agent['cause']) in failures:
                    failures.remove('{0} - {1}'.format(agent['name'], agent['cause']))
                    break

    if not failures:
        failures.append('There are currently no notable agent failures.')

    if not captcha:
        captcha.append('There are currently no notable unscrapable agents.')

    if not credentials:
        credentials.append('There are currently no notable login credential agents falures.')

    return failures, captcha, credentials


def get_key_from_classname(classname):
    return classname.split('.')[3][5:].replace('_', ' ')


def generate_message(test_results, bad_agents):
    test_suite = test_results['testsuite']
    end_site_down = []
    error_count = 0

    for test_case in test_suite['testcase']:
        key_name = get_key_from_classname(test_case['@classname'])
        if 'failure' in test_case or 'error' in test_case:
            if 'failure' in test_case and 'END_SITE_DOWN' in test_case['failure']['@message']:
                end_site_down.append(key_name)
                continue
            error_count += 1

    failures, captcha, credentials = generate_failures_and_warnings(bad_agents)

    return {
        'failures': failures,
        'captcha': captcha,
        'credentials': credentials,
        'end_site_down': ', '.join(sorted(list(set(end_site_down)), reverse=True)) or None,
        'error_info': '*Total errors:* {0}/{1}\n*Time:* {2} seconds\n'.format(error_count,
                                                                              test_suite['@tests'],
                                                                              test_suite['@time']),
    }


def get_error_from_test_case(test_case):
    has_error = False

    error_text = None
    if 'error' in test_case:
        has_error = True
        error_text = test_case['error']['#text']
    elif 'failure' in test_case:
        has_error = True
        error_text = test_case['failure']['#text']
    return has_error, error_text


def get_error_cause(error_text):
    # attempt to pick out an error cause in the error text.
    error_cause = '(no cause)'
    if error_text:
        for regex in error_cause_regexes:
            match = regex.findall(error_text)
            if len(match) > 0:
                error_cause = next(s for s in match if s)[0:128]
                break
    return error_cause


def get_problematic_agents(test_results):
    parsed_results = parse_test_results(test_results)

    agents = []
    for class_name, result in parsed_results.items():
        if result['count'] > 0:
            agents.append({
                'classname': class_name,
                'name': class_name.replace('test_', '', 1).replace('_', ' '),
                'cause': result['cause']
            })
    return agents


def parse_test_results(test_results):
    test_suite = test_results['testsuite']
    parsed_results = {}

    for test_case in test_suite['testcase']:
        classname = test_case['@classname'].split('.')[3]

        has_error, error_text = get_error_from_test_case(test_case)
        error_cause = get_error_cause(error_text)

        if classname in parsed_results:
            if has_error:
                parsed_results[classname]['count'] += 1
                if not parsed_results[classname]['cause']:
                    parsed_results[classname]['cause'] = '{}...'.format(error_cause.strip())
        else:
            parsed_results[classname] = {
                'count': 1 if has_error else 0,
                'cause': '{}...'.format(error_cause.strip()) if has_error else None,
            }
    return parsed_results


def resolve_issue(classname):
    influx.query("drop series from test_results where classname = '{}'".format(classname))
    key = get_key_from_classname(classname)
    Slacker(SLACK_API_KEY).chat.post_message('#errors-agents',
                                             '_The issue with {} has been marked as resolved._'.format(key))


def test_single_agent(a):
    update_credentials()
    a = a.replace(" ", "_")
    py_test = join(os.path.dirname(sys.executable), 'pytest')
    junit_single_agent_xml = 'tests_results/test_' + a + '.xml'
    subprocess.call([py_test, '--junitxml', junit_single_agent_xml, test_path + "test_" + a + ".py"])
    return junit_single_agent_xml


def run_agent_tests():
    update_credentials()
    py_test = join(os.path.dirname(sys.executable), 'pytest')
    subprocess.call([py_test, '-n', str(parallel_processes), '--junitxml', JUNIT_XML_FILENAME, test_path])


def get_formatted_message(xml_file_path):
    with open(xml_file_path) as f:
        test_results = xmltodict.parse(f.read())

    bad_agents = get_problematic_agents(test_results)
    message = generate_message(test_results, bad_agents)
    return message


def send_to_helios(data, running_tests=False):
    data['running_tests'] = running_tests
    try:
        requests.post(HELIOS_URL + '/data_point/', json=data)
    except requests.exceptions.RequestException:
        pass


def get_agent_list():
    return {
        agent.split('.')[0]: agent.split('.')[0].replace('_', ' ')
        for agent in AGENTS.values()
        if agent != 'my360.My360'
    }


if __name__ == '__main__':
    send_to_helios({}, running_tests=True)
    run_agent_tests()
    # Alert our heart beat service that we are in fact running
    requests.get(HEARTBEAT_URL)

    msg = get_formatted_message(JUNIT_XML_FILENAME)
    post_formatted_slack_message(msg)
    agents = get_agent_list()
    helios = dict(agents=agents, errors=msg)
    send_to_helios(helios)
