#!/usr/bin/env python3
'''
This script is to run as a cron to provide the junit xml for the apollo service to view
'''

import sys
import os
from os.path import join
import requests
import subprocess
import xmltodict
from settings import SLACK_API_KEY, APOLLO_URL, JUNIT_XML_FILENAME, HEARTBEAT_URL,\
    INFLUX_HOST, INFLUX_PORT, INFLUX_USER, INFLUX_PASSWORD, INFLUX_DATABASE
from slacker import Slacker
from influxdb import InfluxDBClient
import re

test_path = 'app/tests/service/'
parallel_processes = 4

influx = InfluxDBClient(INFLUX_HOST, INFLUX_PORT, INFLUX_USER, INFLUX_PASSWORD, INFLUX_DATABASE)

# the number of hours of failure considered to be problematic for an agent
PROBLEMATICAL_THRESHOLD = 6

# regexes that can help pull error causes out of test errors and failures.
# these are ordered from most to least helpful. if the most helpful one fails, the next is tried, and so on.
error_cause_regexes = [
    re.compile(r'^E.*?app\.agents\.exceptions\.(.*?)$', re.MULTILINE),
    re.compile(r'^E\s*\-\s*(.*)$', re.MULTILINE),
    re.compile(r'^E\s*(.*)$', re.MULTILINE),
]


def generate_failures_and_warnings(bad_agents):
    failures = []
    captcha = []

    captcha_flags = [
        'captcha',
        'ip blocked',
    ]

    # makes sure end site down errors are not considered again
    ignored_flags = [
        'end site down',
    ]

    for agent in bad_agents:
        resolve_url = 'http://dev.midas.loyaltyangels.local/resolve_issue/{}'.format(agent['classname'])
        for captcha_flag in captcha_flags:
            if captcha_flag in agent['cause'].lower():
                captcha.append('(<{2}|resolve>) {0} - {1}'.format(agent['name'], agent['cause'], resolve_url))
                break
            else:
                failures.append('(<{2}|resolve>) {0} - {1}'.format(agent['name'], agent['cause'], resolve_url))
                break
        # takes out all the errors that should be ignored
        for ignored_flag in ignored_flags:
            if ignored_flag in agent['cause'].lower():
                if '(<{2}|resolve>) {0} - {1}'.format(agent['name'], agent['cause'], resolve_url) in failures:
                    failures.remove('(<{2}|resolve>) {0} - {1}'.format(agent['name'], agent['cause'], resolve_url))
                    break

    if len(failures) == 0:
        failures.append('_There are currently no notable agent failures._')

    if len(captcha) == 0:
        captcha.append('_There are currently no notable unscrapable agents._')

    return failures, captcha


def get_key_from_classname(classname):
    return classname.split('.')[0][5:].replace('_', ' ')


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

    failures, captcha = generate_failures_and_warnings(bad_agents)

    return ('*Total errors:* {0}/{6}\n*Time:* {4} seconds\n\n'
            '*Errors*\n{1}\n\n*The Unscrapables*\n{2}\n\n*End site down:* {3}\n{5}').format(
        error_count,
        '\n'.join('>{}'.format(f) for f in failures),
        '\n'.join('>{}'.format(w) for w in captcha),
        ', '.join(set(end_site_down)) or None,
        test_suite['@time'],
        '{0}/#/exceptions/'.format(APOLLO_URL),
        test_suite['@tests']
    )


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


def parse_test_results(test_results):
    test_suite = test_results['testsuite']
    parsed_results = {}

    for test_case in test_suite['testcase']:
        classname = test_case['@classname'].split('.')[0]

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
                'cause': None,
            }
    return parsed_results


def write_to_influx(test_results):
    parsed_results = parse_test_results(test_results)
    points = []
    for classname, error in parsed_results.items():
        points.append({
            'measurement': 'test_results',
            'tags': {
                'classname': classname
            },
            'fields': {
                'errored': error['count'] > 0,
                'cause': error['cause']
            }
        })
    influx.write_points(points)


def get_problematic_agents():
    bad_agents = []
    tags = influx.query('show tag values from test_results with key = classname')
    for tag in tags.get_points():
        errors = influx.query("select cause "
                              "from test_results "
                              "where time > now() - 24h "
                              "and errored = true "
                              "and classname = '{}'".format(tag['classname']))

        points = list(errors.get_points())
        if len(points) >= PROBLEMATICAL_THRESHOLD:
            bad_agents.append({
                'classname': tag['classname'],
                'name': tag['classname'].replace('test_', '', 1).replace('_', ' '),
                'cause': points[0]['cause'],
            })
    return bad_agents


def resolve_issue(classname):
    influx.query("drop series from test_results where classname = '{}'".format(classname))
    key = get_key_from_classname(classname)
    Slacker(SLACK_API_KEY).chat.post_message('#errors-agents',
                                             '_The issue with {} has been marked as resolved._'.format(key))

if __name__ == '__main__':
    py_test = join(os.path.dirname(sys.executable), 'py.test')
    result = subprocess.call([py_test, '-n', str(parallel_processes), '--junitxml', JUNIT_XML_FILENAME, test_path])

    # Alert our heart beat service that we are in fact running
    requests.get(HEARTBEAT_URL)

    with open(JUNIT_XML_FILENAME) as f:
        test_results = xmltodict.parse(f.read())
    write_to_influx(test_results)
    bad_agents = get_problematic_agents()
    message = generate_message(test_results, bad_agents)
    Slacker(SLACK_API_KEY).chat.post_message('#errors-agents', message)
