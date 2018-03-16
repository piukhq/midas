import importlib
import lxml.html
import re
from Crypto import Random
from decimal import Decimal
from app.active import AGENTS

TWO_PLACES = Decimal(10) ** -2


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


def get_config(merchant_id, handler_type):
    """
    TODO: get config from helios database
    :param merchant_id:
    :param handler_type:
    :return:
    """
    return {'log_level': 'DEBUG'}
