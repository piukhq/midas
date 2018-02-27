import hashlib
from decimal import Decimal
from collections import defaultdict
from urllib.parse import urlsplit

import _ssl
import requests
from requests import Session, HTTPError
from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout, Timeout
from requests.packages.urllib3.poolmanager import PoolManager
from robobrowser import RoboBrowser
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from app.utils import open_browser, TWO_PLACES, pluralise
from app.agents.exceptions import AgentError, LoginError, END_SITE_DOWN, UNKNOWN, RETRY_LIMIT_REACHED, \
    IP_BLOCKED, RetryLimitError, STATUS_LOGIN_FAILED, TRIPPED_CAPTCHA
from app.publish import put
from settings import HERMES_URL


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


class BaseMiner(object):
    retry_limit = 2
    point_conversion_rate = Decimal('0')
    connect_timeout = 1
    known_captcha_signatures = [
        'recaptcha',
        'captcha',
        'Incapsula',
    ]
    identifier_type = None
    identifier = None

    def register(self, credentials):
        raise NotImplementedError()

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def scrape_transactions(self):
        raise NotImplementedError()

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def calculate_label(self, points):
        raise NotImplementedError()

    def transactions(self):
        return self.hash_transactions([self.parse_transaction(t) for t in self.scrape_transactions()])

    def hash_transactions(self, transactions):
        count = defaultdict(int)

        for transaction in transactions:
            s = "{0}{1}{2}{3}{4}".format(transaction['date'], transaction['description'],
                                         transaction['points'], self.scheme_id, transaction.get('location'))

            # identical hashes get sequentially indexed to make them unique.
            index = count[s]
            count[s] += 1
            s = "{0}{1}".format(s, index)
            transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()

        return transactions

    def calculate_point_value(self, points):
        return (points * self.point_conversion_rate).quantize(TWO_PLACES)

    def account_overview(self):
        return {
            'balance': self.balance(),
            'transactions': self.transactions()
        }

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

    @staticmethod
    def update_questions(questions):
        return questions

    def attempt_login(self, credentials):
        if self.retry_count >= self.retry_limit:
            raise RetryLimitError(RETRY_LIMIT_REACHED)

        try:
            self.login(credentials)
        except KeyError as e:
            raise Exception("missing the credential '{0}'".format(e.args[0]))

    def attempt_register(self, credentials):
        try:
            self.register(credentials)
        except KeyError as e:
            raise Exception("missing the credential '{0}'".format(e.args[0]))

    @staticmethod
    def update_scheme_account(scheme_account_id, message, tid, identifier=None):
        """
        Send an identifier to hermes and a message of success or an error message if there was a problem
        retrieving the identifier.

        :param scheme_account_id: id of scheme account to update
        :param message: details such as error message or "success"
        :param tid: transaction id
        :param identifier: identifier credential e.g membership id, barcode.
        """
        data = {
            'message': message,
            'identifier': identifier,
        }
        put('{}/schemes/accounts/{}/join'.format(HERMES_URL, scheme_account_id), data, tid)
        return data


# Based on RoboBrowser Library
class RoboBrowserMiner(BaseMiner):

    use_tls_v1 = False

    ################################################################################
    # ALERT: When changing this, check other agents with their own __init__ method
    ################################################################################

    def __init__(self, retry_count, scheme_id, scheme_slug=None):
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.headers = {}
        self.proxy = False

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

    def open_url(self, url, method='get', read_timeout=5, **kwargs):
        """
        Sensible defaults and error handling for opening url
        http://www.mobify.com/blog/http-requests-are-hard/
        """
        connect_timeout = self.connect_timeout

        # Combine the passed kwargs with our headers and timeout values.
        args = {
            'headers': self.headers,
            'timeout': (connect_timeout, read_timeout)
        }
        args.update(kwargs)

        try:
            self.browser.open(url, method=method, **args)
        except ReadTimeout as exception:
            raise AgentError(END_SITE_DOWN) from exception

        try:
            self.browser.response.raise_for_status()
        except HTTPError as e:
            self._raise_agent_exception(e)

        self.find_captcha()

    def _raise_agent_exception(self, exc):
        """ Raises an agent exception depending on the exc code
        if needed: overwrite it on the child agent class to personalise it
        :param exc: exception (HTTPError)
        """
        if exc.response.status_code == 401:
            raise LoginError(STATUS_LOGIN_FAILED)
        elif exc.response.status_code == 403:
            raise AgentError(IP_BLOCKED) from exc

        raise AgentError(END_SITE_DOWN) from exc

    def find_captcha(self):
        """Look for CAPTCHA on the page"""
        frame_urls = (frame['src'] for frame in self.browser.select('iframe') if 'src' in frame)
        for url in frame_urls:
            for sig in self.known_captcha_signatures:
                if sig in url:
                    raise AgentError(TRIPPED_CAPTCHA)

        if self.browser.select('#recaptcha_widget'):
            raise AgentError(TRIPPED_CAPTCHA)

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


# Based on requests library
class ApiMiner(BaseMiner):

    def __init__(self, retry_count, scheme_id, scheme_slug=None):
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.headers = {}
        self.retry_count = retry_count
        self.errors = {}

    def make_request(self, url, method='get', timeout=5, **kwargs):
        # Combine the passed kwargs with our headers and timeout values.
        args = {
            'headers': self.headers,
            'timeout': timeout,
        }
        args.update(kwargs)

        try:
            resp = requests.request(method, url=url, **args)
        except Timeout as exception:
            raise AgentError(END_SITE_DOWN) from exception

        try:
            resp.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 401:
                raise LoginError(STATUS_LOGIN_FAILED)
            elif e.response.status_code == 403:
                raise AgentError(IP_BLOCKED) from e
            raise AgentError(END_SITE_DOWN) from e

        return resp

    def handle_errors(self, response, exception_type=LoginError):
        for key, values in self.errors.items():
            if response in values:
                raise exception_type(key)
        raise AgentError(UNKNOWN)


# Based on Selenium library and headless Firefox
class SeleniumMiner(BaseMiner):

    def __init__(self, retry_count, scheme_id, scheme_slug=None):
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.headers = {}
        self.retry_count = retry_count
        self.setup_browser()

    def selenium_handler(selenium_function):
        def handled(self, *args):
            try:
                selenium_function(self, *args)

            except Exception as e:
                self.browser.quit()
                raise e

        return handled

    @selenium_handler
    def setup_browser(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--hide-scrollbars')
        options.add_argument('--disable-gpu')
        self.browser = webdriver.Firefox(firefox_options=options, log_path=None)
        self.browser.implicitly_wait(5)

    def attempt_login(self, credentials):
        super().attempt_login(credentials)
        self.browser.quit()

    def find_captcha(self):
        for captcha in self.known_captcha_signatures:
            if self.browser.find_elements_by_xpath('//iframe[contains(@src, "{}")]'.format(captcha)):
                raise AgentError(TRIPPED_CAPTCHA)

    def view(self):
        """
        Open the current state of the headless browser in a non-headless browser
        """
        parts = urlsplit(self.browser.current_url)
        base_href = "{0}://{1}".format(parts.scheme, parts.netloc)
        open_browser(self.browser.page_source.encode('utf-8'), base_href)
