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
    return Decimal(re.search(r'-?\d*\.{0,1}\d+', s).group(0)).quantize(TWO_PLACES)


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
