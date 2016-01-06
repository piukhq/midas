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


def generate_message(test_results):
    test_suite = test_results["testsuite"]
    failures = defaultdict(list)
    end_site_down = []
    error_count = 0

    for test_case in test_suite["testcase"]:
        key_name = test_case["@classname"].split(".")[0][5:].replace('_', ' ')
        if "failure" in test_case or "error" in test_case:
            if 'failure' in test_case and 'END_SITE_DOWN' in test_case['failure']['@message']:
                end_site_down.append(key_name)
                continue
            error_count += 1
            failures[key_name].append(test_case["@name"].replace('_', ' '))

    failures_str = "\n".join(["{0}: {1}".format(agent.title(), errors) for agent, errors in failures.items()])

    return "*Total errors:* {0} \n*Time:* {3} seconds \n\n{1} \n\n *End site down:* {2}\n {4}".format(
        error_count, failures_str, ", ".join(end_site_down), test_suite['@time'], "{0}/#/exceptions/".format(APOLLO_URL)
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
        Slacker(SLACK_API_KEY).chat.post_message('#errors', message)
