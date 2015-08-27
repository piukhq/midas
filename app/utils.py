import lxml.html
import re
from Crypto import Random
from decimal import Decimal
from urllib.parse import urlsplit


def extract_decimal(s):
    return Decimal(re.sub(r'[^\d.]+', '', s.strip()))


def open_browser(b):
    parts = urlsplit(b.url)
    base_href = "{0}://{1}".format(parts.scheme, parts.netloc)

    html = lxml.html.fromstring(b.parsed.prettify("utf-8"))
    html.make_links_absolute(base_href, resolve_base_href=True)

    lxml.html.open_in_browser(html)


def generate_random_key():
    Random.get_random_bytes(128)
