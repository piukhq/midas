import hashlib
import json
from decimal import Decimal
from collections import defaultdict
import os
import signal
from urllib.parse import urlsplit

import _ssl
from uuid import uuid4

import requests
from requests import Session, HTTPError
from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout, Timeout
from requests.packages.urllib3.poolmanager import PoolManager
from robobrowser import RoboBrowser
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from contextlib import contextmanager

from app import utils
from app.configuration import Configuration
from app.security import get_security_agent
from settings import logger
from app.utils import open_browser, TWO_PLACES, pluralise, create_error_response
from app.agents.exceptions import AgentError, LoginError, END_SITE_DOWN, UNKNOWN, RETRY_LIMIT_REACHED, \
    IP_BLOCKED, RetryLimitError, STATUS_LOGIN_FAILED, TRIPPED_CAPTCHA, NOT_SENT, errors, NO_SUCH_RECORD, \
    ACCOUNT_ALREADY_EXISTS
from app.publish import thread_pool_executor


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
    connect_timeout = 3
    known_captcha_signatures = [
        'recaptcha',
        'captcha',
        'Incapsula',
    ]
    identifier_type = None
    identifier = None
    async = False

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
        try:
            return self.hash_transactions([self.parse_transaction(t) for t in self.scrape_transactions()])
        except Exception:
            return []

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


# Based on RoboBrowser Library
class RoboBrowserMiner(BaseMiner):

    use_tls_v1 = False

    ################################################################################
    # ALERT: When changing this, check other agents with their own __init__ method
    ################################################################################

    def __init__(self, retry_count, scheme_id, scheme_slug=None, account_status=None):
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.account_status = account_status
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

    @staticmethod
    def get_requests_cacert():
        cacert_file = os.path.dirname(requests.__file__) + '/cacert.pem'
        if os.path.isfile(cacert_file):
            return cacert_file

        # verify = True will mean requests uses certifi's cacert.pem for verifying ssl connections
        return True


# Based on requests library
class ApiMiner(BaseMiner):

    def __init__(self, retry_count, scheme_id, scheme_slug=None, account_status=None):
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.account_status = account_status
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

    def __init__(self, retry_count, scheme_id, scheme_slug=None, account_status=None):
        self.delay = 15
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.account_status = account_status
        self.headers = {}
        self.retry_count = retry_count
        self.setup_browser()

    def selenium_handler(selenium_function):
        def handled(self, *args):
            try:
                selenium_function(self, *args)

            except Exception as e:
                self.close_selenium()
                raise e

        return handled

    @selenium_handler
    def setup_browser(self):
        options = webdriver.firefox.options.Options()
        options.add_argument('--headless')
        options.add_argument('--hide-scrollbars')
        options.add_argument('--disable-gpu')
        self.browser = webdriver.Firefox(firefox_options=options, log_path=None)
        self.browser.implicitly_wait(self.delay)

    @selenium_handler
    def attempt_login(self, credentials):

        super().attempt_login(credentials)
        self.close_selenium()

    def find_captcha(self):
        self.browser.implicitly_wait(1)
        for captcha in self.known_captcha_signatures:
            if self.browser.find_elements_by_xpath('//iframe[contains(@src, "{}")]'.format(captcha)):
                raise AgentError(TRIPPED_CAPTCHA)
        self.browser.implicitly_wait(self.delay)

    def view(self):
        """
        Open the current state of the headless browser in a non-headless browser
        """
        parts = urlsplit(self.browser.current_url)
        base_href = "{0}://{1}".format(parts.scheme, parts.netloc)
        open_browser(self.browser.page_source.encode('utf-8'), base_href)

    def close_selenium(self):
        pid = self.browser.service.process.pid
        self.browser.quit()

        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    @contextmanager
    def wait_for_page_load(self, timeout=15):
        old_page = self.browser.find_element_by_tag_name('html')
        yield
        WebDriverWait(self.browser, timeout).until(
            ec.staleness_of(old_page)
        )

    def wait_for_value(self, css_selector, text, timeout=15):
        WebDriverWait(self.browser, timeout).until(
            ec.text_to_be_present_in_element((webdriver.common.by.By.CSS_SELECTOR, css_selector), text)
        )


class MerchantApi(BaseMiner):

    def __init__(self, retry_count, scheme_id, scheme_slug=None, account_status=None):
        self.retry_count = retry_count
        self.scheme_id = scheme_id
        self.scheme_slug = scheme_slug
        self.account_status = account_status

        # { error we raise: error we receive in merchant payload}
        self.errors = {
            NO_SUCH_RECORD: ['NO_SUCH_RECORD'],
            STATUS_LOGIN_FAILED: ['VALIDATION'],
            ACCOUNT_ALREADY_EXISTS: ['ALREADY_PROCESSED'],
            UNKNOWN: ['GENERAL_ERROR']
        }

    def login(self, credentials):
        """
        Calls handler, passing in handler_type as either 'validate' or 'update' depending on if a link
        request was made or not. A link boolean should be in the credentials to check if request was a link.
        :param credentials: user account credentials for merchant scheme
        :return: None
        """
        handler_type = 'validate' if self.account_status == 'WALLET_ONLY' else 'update'

        self.result = self._outbound_handler(credentials, self.scheme_slug, handler_type=handler_type)

        error = self.result['error_codes']
        if error:
            self.handle_errors(error[0]['description'])

    def register(self, data, inbound=False):
        """
        Calls handler, passing in 'join' as the handler_type.
        :param data: user account credentials to register for merchant scheme or merchant response for outbound
                     or inbound processes respectively.
        :param inbound: Boolean for if the data should be handled for an inbound response or outbound request
        :return: None
        """
        if inbound:
            self._async_inbound(data, self.scheme_slug, handler_type='join')
        else:
            self.result = self._outbound_handler(data, self.scheme_slug, handler_type='join')

            error = self.result['error_codes']
            if error:
                self.handle_errors(error[0]['description'])

    # Should be overridden in the agent if there is agent specific processing required for their response.
    def process_join_response(self, response):
        """
        Processes a merchant's response to a join request.
        :param response: JSON data of a merchant's response
        :return: None
        """
        # check for error response

        # link account (get balance and transactions)

        raise NotImplementedError()

    def _outbound_handler(self, data, merchant_id, handler_type):
        """
        Handler service to apply merchant configuration and build JSON, for request to the merchant, and
        handles response. Configuration service is called to retrieve merchant config.
        :param data: python object data to be built into the JSON object.
        :param merchant_id: Bink's unique identifier for a merchant (slug)
        :param handler_type: type of handler to retrieve correct config e.g update, validate, join
        :return: dict of response data
        """
        message_uid = str(uuid4())

        config = Configuration(merchant_id, handler_type)

        data['message_uid'] = message_uid
        data['callback_url'] = config.callback_url

        payload = json.dumps(data)

        # log payload
        # TODO: logging setup for _outbound_handler
        logger.info("TODO: logging setup for _outbound_handler")

        response_data = self._sync_outbound(payload, config)

        if response_data and config['log_level']:
            # log json_data
            # TODO: logging setup for _outbound_handler
            logger.info("TODO: logging setup for _outbound_handler")

        return json.loads(response_data)

    def _inbound_handler(self, json_data, merchant_id):
        """
        Handler service for inbound response i.e. response from async join. The response json is logged,
        converted to a python object and passed to the relevant method for processing.
        :param json_data: JSON payload
        :param merchant_id: Bink's unique identifier for a merchant (slug)
        :return: dict of response data
        """
        # log json_data
        # TODO: logging setup for _outbound_handler
        logger.info("TODO: logging setup for _inbound_handler {}".format(merchant_id))

        return self.process_join_response(json.loads(json_data))

    def _sync_outbound(self, data, config):
        """
        Synchronous outbound service to build a request and make call to merchant endpoint.
        Calls are made to security and back off services pre-request.
        :param data: JSON string of payload to send to merchant
        :param config: dict of merchant configuration settings
        :return: Response payload
        """

        security_agent = get_security_agent(config['security_service'], config['security_credentials'])
        request = security_agent.encode(data)

        for retry_count in range(1 + config['retry_limit']):
            if BackOffService.is_on_cooldown(config['merchant_id'], config['handler_type']):
                response_json = create_error_response(errors[NOT_SENT]['code'], errors[NOT_SENT]['name'])
                break
            else:
                response = requests.post(config['merchant_url'], **request)
                status = response.status_code

                if status == 200:
                    response_json = security_agent.decode(response)
                    # Check if request was redirected
                    # TODO: logging for redirects
                    if response.history:
                        logger.warning("TODO: logging setup for redirect in _sync_outbound")
                    break

                elif status in [503, 504, 408]:
                    response_json = create_error_response(errors[NOT_SENT]['code'], errors[NOT_SENT]['name'])
                else:
                    response_json = create_error_response(errors[UNKNOWN]['code'],
                                                          errors[UNKNOWN]['name'] + ' with status code {}'
                                                          .format(status))

                if retry_count == config['retry_limit']:
                    BackOffService.activate_cooldown(config['merchant_id'], config['handler_type'], 100)

        return response_json

    def _async_inbound(self, response, merchant_id, handler_type):
        """
        Asynchronous inbound service that will decode json based on configuration per merchant and return
        a success response asynchronously before calling the inbound handler service.
        :param response: Response object
        :param merchant_id: Bink's unique identifier for a merchant (slug)
        :return: None
        """
        config = Configuration(merchant_id, handler_type)

        security_agent = get_security_agent(config.security_service, config.security_credentials)
        decoded_data = security_agent.decode(response)

        # asynchronously call handler
        thread_pool_executor.submit(self._inbound_handler, decoded_data, self.scheme_slug, handler_type)

    def handle_errors(self, response, exception_type=LoginError):
        for key, values in self.errors.items():
            if response in values:
                raise exception_type(key)
        raise AgentError(UNKNOWN)


class BackOffService:
    # TODO: Remove when implementing the back off service
    @classmethod
    def is_on_cooldown(cls, merchant_id, handler_type):
        print('cooldown checked for {}/{}'.format(merchant_id, handler_type))
        return False

    @classmethod
    def activate_cooldown(cls, merchant_id, handler_type, time):
        print('activated cooldown for {}/{} of {} seconds'.format(merchant_id, handler_type, time))
