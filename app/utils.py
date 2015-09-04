import importlib
from arrow import Arrow
import lxml.html
import re
from Crypto import Random
from decimal import Decimal
import simplejson
from app.active import AGENTS


def extract_decimal(s):
    return Decimal(re.search(r'-?\d*\.{0,1}\d+', s).group(0))


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


class ArrowEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Arrow):
            return obj.format('YYYY-MM-DD HH:mm:ss ZZ')

        return simplejson.JSONEncoder.default(self, obj)
