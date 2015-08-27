import lxml.html
import re
from decimal import Decimal


def extract_decimal(s):
    return Decimal(re.sub(r'[^\d.]+', '', s.strip()))

def open_browser(s, base_href):
    html = lxml.html.fromstring(s.parsed.prettify("utf-8"))
    html.make_links_absolute(base_href, resolve_base_href=True)

    lxml.html.open_in_browser(html)
