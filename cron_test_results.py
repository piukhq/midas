#!/usr/bin/env python3
"""
This script is to run as a cron to provide the junit xml for the apollo service to view
"""

import sys
import os
from os.path import join
import requests
import subprocess
import xmltodict
from collections import defaultdict
from settings import SLACK_API_KEY, APOLLO_URL, JUNIT_XML_FILENAME, HEARTBEAT_URL
from slacker import Slacker

test_path = "app/tests/service/"
parallel_processes = 4


def format_table(failures):
    # invert the dictionary
    columns = defaultdict(list)
    for name, failure_set in failures.items():
        for failure in failure_set:
            columns[failure].append(name)

    # get the Y axis width as the maximum length of a scheme name.
    bar_width = max((len(x) for x in failures.keys())) + 1
    inner_bar_width = bar_width - 1

    # generate a heading containing all column names and a horizontal rule below them
    heading = '{0}│'.format(' ' * inner_bar_width)
    column_widths = {}
    for column in columns.keys():
        column_widths[column] = len(column) + 4
        heading += '{0:^{1}}'.format(column, column_widths[column])

    # build the separator between headings and values
    total_width = sum(column_widths.values())
    heading += '\n{0}┼{1}'.format('─' * inner_bar_width, '─' * total_width)

    # fill in the Y axis names, and put X's in each column where that row has a failure.
    lines = [''] * len(failures.keys())
    for line, name in enumerate(failures.keys()):
        lines[line] = '{0:>{1}s}│'.format(name.title(), inner_bar_width)

        failure_set = failures[name]
        for column in columns.keys():
            width = column_widths[column]
            if column in failure_set:
                lines[line] += '{0:·^{1}}'.format('╳', width)
            else:
                lines[line] += '·' * width

    return '{0}\n{1}'.format(heading, '\n'.join(lines))


def parse_test_results(test_results):
    test_suite = test_results["testsuite"]
    failures = defaultdict(list)

    for test_case in test_suite["testcase"]:
        key_name = test_case["@classname"].split(".")[0][5:].replace('_', ' ')
        if "failure" in test_case or "error" in test_case:
            failures[key_name].append(test_case["@name"].replace('_', ' '))

    return failures


def generate_message(test_results):
    failures = parse_test_results(test_results)

    test_suite = test_results["testsuite"]
    end_site_down = []
    error_count = 0

    for test_case in test_suite["testcase"]:
        key_name = test_case["@classname"].split(".")[0][5:].replace('_', ' ')
        if "failure" in test_case or "error" in test_case:
            if 'failure' in test_case and 'END_SITE_DOWN' in test_case['failure']['@message']:
                end_site_down.append(key_name)
                continue
            error_count += 1

    failures_str = '```{}```'.format(format_table(failures))

    return "*Total errors:* {0}/{5} \n*Time:* {3} seconds \n\n{1} \n\n *End site down:* {2}\n {4}".format(
        error_count, failures_str, ", ".join(end_site_down) or None, test_suite['@time'],
        "{0}/#/exceptions/".format(APOLLO_URL), test_suite["@tests"]
    )


if __name__ == '__main__':
    py_test = join(os.path.dirname(sys.executable), "py.test")
    result = subprocess.call([py_test, "-n", str(parallel_processes), "--junitxml", JUNIT_XML_FILENAME, test_path])

    # Alert our heart beat service that we are in fact running
    requests.get(HEARTBEAT_URL)

    if result == 0:
        print("All tests passed")
    else:
        with open(JUNIT_XML_FILENAME) as f:
            test_results = xmltodict.parse(f.read())
        message = generate_message(test_results)
        Slacker(SLACK_API_KEY).chat.post_message('#errors-agents', message)
