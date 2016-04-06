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


def generate_message(test_results, bad_agents):
    test_suite = test_results['testsuite']
    end_site_down = []
    error_count = 0

    for test_case in test_suite['testcase']:
        key_name = test_case['@classname'].split('.')[0][5:].replace('_', ' ')
        if 'failure' in test_case or 'error' in test_case:
            if 'failure' in test_case and 'END_SITE_DOWN' in test_case['failure']['@message']:
                end_site_down.append(key_name)
                continue
            error_count += 1

    failures = []
    for agent in bad_agents:
        failures.append('{} - {}'.format(agent['name'], agent['cause']))

    if len(failures) == 0:
        failures.append('_There are currently no notable agent failures._')

    return '*Total errors:* {0}/{5}\n*Time:* {3} seconds\n\n{1}\n\n *End site down:* {2}\n{4}'.format(
        error_count, '\n'.join('>{}'.format(f) for f in failures), ', '.join(end_site_down) or None, test_suite['@time'],
        '{0}/#/exceptions/'.format(APOLLO_URL), test_suite['@tests']
    )


def write_to_influx(test_results):
    test_suite = test_results['testsuite']
    parsed_results = {}

    for test_case in test_suite['testcase']:
        classname = test_case['@classname'].split('.')[0]

        has_error = False

        error_text = None
        if 'error' in test_case:
            has_error = True
            error_text = test_case['error']['#text']
        elif 'failure' in test_case:
            has_error = True
            error_text = test_case['failure']['#text']

        # attempt to pick out an error cause in the error text.
        error_cause = '(no cause)'
        if error_text:
            for regex in error_cause_regexes:
                match = regex.findall(error_text)
                if len(match) > 0:
                    error_cause = next(s for s in match if s)[0:128]
                    break

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
                'name': tag['classname'].replace('test_', '', 1).replace('_', ' '),
                'cause': points[0]['cause'],
            })
    return bad_agents

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
