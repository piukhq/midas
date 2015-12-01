from collections import defaultdict

import hashlib
from requests import HTTPError
from requests.exceptions import ReadTimeout
from robobrowser import RoboBrowser
from urllib.parse import urlsplit
from app.utils import open_browser, TWO_PLACES, pluralise
from app.agents.exceptions import AgentError, LoginError, END_SITE_DOWN, UNKNOWN, RETRY_LIMIT_REACHED, \
    IP_BLOCKED, RetryLimitError, STATUS_LOGIN_FAILED
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from decimal import Decimal
import _ssl


class SSLAdapter(HTTPAdapter):
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        self.poolmanager = PoolManager()
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=self.ssl_version)


class Miner(object):
    retry_limit = 5
    headers = {}
    use_tls_v1 = False
    proxy = False

    point_conversion_rate = Decimal('0')

    def __init__(self, retry_count, scheme_id):
        self.scheme_id = scheme_id
        session = Session()

        if self.use_tls_v1:
            session.mount('https://', SSLAdapter(_ssl.PROTOCOL_TLSv1))

        if self.proxy:
            session.proxies = {'http': 'http://192.168.1.47:3128',
                               'https': 'https://192.168.1.47:3128'}

        self.browser = RoboBrowser(parser="lxml", session=session,
                                   user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) "
                                              "Gecko/20100101 Firefox/40.0")
        self.retry_count = retry_count

    def attempt_login(self, credentials):
        if self.retry_count >= self.retry_limit:
            raise RetryLimitError(RETRY_LIMIT_REACHED)

        try:
            self.login(credentials)
        except KeyError as e:
            raise Exception("missing the credential '{0}'".format(e.args[0]))

    def open_url(self, url, verify=True, method='get', data=None, json=None, read_timeout=5):
        """
        Sensible defaults and error handling for opening url
        http://www.mobify.com/blog/http-requests-are-hard/
        """
        connect_timeout = 1

        try:
            self.browser.open(url, timeout=(connect_timeout, read_timeout),
                              headers=self.headers, verify=verify, method=method, data=data, json=json)
        except ReadTimeout as exception:
            raise AgentError(END_SITE_DOWN) from exception

        try:
            self.browser.response.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 401:
                raise LoginError(STATUS_LOGIN_FAILED)
            elif e.response.status_code == 403:
                raise AgentError(IP_BLOCKED) from e
            raise AgentError(END_SITE_DOWN) from e

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def transactions(self):
        raise NotImplementedError()

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def account_overview(self):
        return {
            'balance': self.balance(),
            'transactions': self.transactions()
        }

    def index_transactions(self, transactions):
        # As far as I can tell, collections.Counter provides no method to incrementally add items.
        count = defaultdict(int)

        for transaction in transactions:
            transaction['index'] = count[transaction['date']]
            count[transaction['date']] += 1

        return transactions

    def hash_transactions(self, transactions):
        transactions = self.index_transactions(list(transactions))

        for transaction in transactions:
            s = "{0}{1}{2}{3}{4}".format(transaction['date'], transaction['description'],
                                         transaction['points'], self.scheme_id,
                                         transaction['index'])
            transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()

        return transactions

    def check_error(self, incorrect, error_causes, url_part="path"):
        parts = urlsplit(self.browser.url)
        if getattr(parts, url_part) != incorrect:
            return

        for error in error_causes:
            selector, error_name, error_match = error
            message = self.browser.select(selector)
            if message and message[0].get_text().strip().startswith(error_match):
                raise LoginError(error_name)
        raise LoginError(UNKNOWN)

    def calculate_point_value(self, points):
        return (points * self.point_conversion_rate).quantize(TWO_PLACES)

    def calculate_label(self, points):
        raise NotImplementedError()

    @staticmethod
    def format_label(count, noun, plural_suffix='s', include_zero_items=False):
        if count == 0 and not include_zero_items:
            return ''
        return '{} {}'.format(count, noun + pluralise(count, plural_suffix))

    # Expects a list of tuples (point threshold, reward string) sorted by threshold from highest to lowest.
    @staticmethod
    def calculate_tiered_reward(points, reward_tiers):
        for threshold, reward in reward_tiers:
            if points >= threshold:
                return reward
        return ''

    def view(self):
        """
        Open the RoboBrowser object in a browser in its current state
        """
        parts = urlsplit(self.browser.url)
        base_href = "{0}://{1}".format(parts.scheme, parts.netloc)
        open_browser(self.browser.parsed.prettify("utf-8"), base_href)
