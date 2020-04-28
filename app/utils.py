import importlib
import json
import re
import socket
from decimal import Decimal
from enum import IntEnum

import lxml.html
from Crypto import Random

from app.active import AGENTS
from settings import SERVICE_API_KEY, logger

TWO_PLACES = Decimal(10) ** -2


class SchemeAccountStatus:
    PENDING = 0
    ACTIVE = 1
    INVALID_CREDENTIALS = 403
    INVALID_MFA = 432
    END_SITE_DOWN = 530
    IP_BLOCKED = 531
    TRIPPED_CAPTCHA = 532
    INCOMPLETE = 5
    LOCKED_BY_ENDSITE = 434
    RETRY_LIMIT_REACHED = 429
    RESOURCE_LIMIT_REACHED = 503
    UNKNOWN_ERROR = 520
    MIDAS_UNREACHABLE = 9
    AGENT_NOT_FOUND = 404
    WALLET_ONLY = 10
    PASSWORD_EXPIRED = 533
    JOIN = 900
    NO_SUCH_RECORD = 444
    JOIN_IN_PROGRESS = 441
    JOIN_ERROR = 538
    GENERAL_ERROR = 439
    CARD_NUMBER_ERROR = 436
    CARD_NOT_REGISTERED = 438
    LINK_LIMIT_EXCEEDED = 437
    JOIN_ASYNC_IN_PROGRESS = 442
    PRE_REGISTERED_CARD = 406
    ENROL_FAILED = 901
    REGISTRATION_FAILED = 902
    ACCOUNT_ALREADY_EXISTS = 445


class JourneyTypes(IntEnum):
    JOIN = 0
    LINK = 1
    ADD = 2
    UPDATE = 3


def extract_decimal(s):
    """
    We need to use the quantize method to ensure whole
    numbers do not become integers when json encoding
    """
    return Decimal(re.search(r'-?\d+(?:,\d+)*(?:\.\d+)?', s).group(0).replace(',', '')).quantize(TWO_PLACES)


def open_browser(html, base_href):
    html = lxml.html.fromstring(html)
    html.make_links_absolute(base_href, resolve_base_href=True)

    lxml.html.open_in_browser(html)


def generate_random_key(n):
    return Random.get_random_bytes(n)


def resolve_agent(name):
    class_path = AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module('app.agents.{}'.format(module_name))
    return getattr(module, class_name)


def pluralise(count, plural_suffix):
    if ',' not in plural_suffix:
        plural_suffix = ',' + plural_suffix
    parts = plural_suffix.split(',')
    if len(parts) > 2:
        return ''
    singular, plural = parts[:2]
    return singular if count == 1 else plural


units = ['k', 'M', 'B', 'T']


def minify_number(n):
    n = int(n)

    if n < 10000:
        return str(n)

    count = 0
    total = n
    while True:
        if total / 1000 > 1:
            total //= 1000
            count += 1
        else:
            break

    return '{0}{1}'.format(total, units[count - 1])


def create_error_response(error_code, error_description):
    response_json = json.dumps({
        'error_codes': [
            {
                'code': error_code,
                'description': error_description
            }
        ]
    })
    return response_json


def get_headers(tid):
    headers = {'Content-type': 'application/json',
               'transaction': str(tid),
               'User-agent': 'Midas on {0}'.format(socket.gethostname()),
               'Authorization': 'token ' + SERVICE_API_KEY}

    return headers


def log_task(func):
    def logged_func(*args, **kwargs):
        try:
            scheme_account_message = ' for scheme account: {}'.format(args[1]['scheme_account_id'])
        except KeyError:
            scheme_account_message = ''

        try:
            logger.debug('starting {0} task{1}'.format(
                func.__name__,
                scheme_account_message
            ))
            result = func(*args, **kwargs)
            logger.debug('finished {0} task{1}'.format(
                func.__name__,
                scheme_account_message
            ))
        except Exception as e:
            logger.debug('error with {0} task{1}. error: {2}'.format(
                func.__name__,
                scheme_account_message,
                repr(e)
            ))
            raise

        return result

    return logged_func
