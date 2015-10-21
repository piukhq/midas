import hashlib
from requests import HTTPError
from robobrowser import RoboBrowser
from urllib.parse import urlsplit
from app.utils import open_browser
from app.agents.exceptions import AgentError, LoginError, END_SITE_DOWN, UNKNOWN, RETRY_LIMIT_REACHED
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import ssl


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
    retry_limit = 2
    headers = {}

    # I'd prefer to set ssl_version to `ssl.PROTOCOL_SSLv2` by default, but that yields:
    # ^- `AttributeError: 'module' object has no attribute 'PROTOCOL_SSLv2'`
    def __init__(self, retry_count, scheme_id, ssl_version=ssl.PROTOCOL_TLSv1_2, proxy=True):
        self.scheme_id = scheme_id
        session = Session()
        session.mount('https://', SSLAdapter(ssl_version))

        if proxy:
            session.proxies = {'http': '[http:192.168.1.40:3128]http:192.168.1.40:3128'}
        self.browser = RoboBrowser(parser="lxml", session=session,
                                   user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) "
                                              "Gecko/20100101 Firefox/40.0")
        self.retry_count = retry_count

    def attempt_login(self, credentials):
        if self.retry_count <= self.retry_limit:
            self.login(credentials)
        else:
            raise AgentError(RETRY_LIMIT_REACHED)

    def open_url(self, url):
        """
        Sensible defaults and error handling for opening url
        http://www.mobify.com/blog/http-requests-are-hard/
        """
        connect_timeout = 1
        read_timeout = 5

        self.browser.open(url, timeout=(connect_timeout, read_timeout), headers=self.headers)

        try:
            self.browser.response.raise_for_status()
        except HTTPError as e:
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

    def hashed_transaction(self, transaction):
        transaction = self.parse_transaction(transaction)
        s = "{0}{1}{2}{3}".format(transaction['date'], transaction['description'],
                                  transaction['points'], self.scheme_id)
        transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()
        return transaction

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

    def view(self):
        """
        Open the RoboBrowser object in a browser in its current state
        """
        parts = urlsplit(self.browser.url)
        base_href = "{0}://{1}".format(parts.scheme, parts.netloc)
        open_browser(self.browser.parsed.prettify("utf-8"), base_href)