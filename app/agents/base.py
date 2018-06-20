import _ssl
import hashlib
import json
import os
import time
from collections import defaultdict
from contextlib import contextmanager
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import uuid1
from random import randint

import requests
import arrow
from requests import Session, HTTPError
from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout, Timeout
from requests.packages.urllib3.poolmanager import PoolManager
from robobrowser import RoboBrowser
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from app import publish
from app.back_off_service import BackOffService
from app.configuration import Configuration
from app.constants import ENCRYPTED_CREDENTIALS
from app.encryption import hash_ids
from app.agents.exceptions import AgentError, LoginError, END_SITE_DOWN, UNKNOWN, RETRY_LIMIT_REACHED, \
    IP_BLOCKED, RetryLimitError, STATUS_LOGIN_FAILED, TRIPPED_CAPTCHA, NOT_SENT, errors, NO_SUCH_RECORD, \
    ACCOUNT_ALREADY_EXISTS, RESOURCE_LIMIT_REACHED
from app.exceptions import AgentException
from app.publish import thread_pool_executor
from app.resources import update_pending_join_account
from app.security.utils import get_security_agent
from app.selenium_pid_store import SeleniumPIDStore
from app.utils import open_browser, TWO_PLACES, pluralise, create_error_response, SchemeAccountStatus
from settings import logger, BACK_OFF_COOLDOWN


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

    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.scheme_id = user_info['scheme_account_id']
        self.scheme_slug = scheme_slug
        self.account_status = user_info['status']
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

    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.scheme_id = user_info['scheme_account_id']
        self.scheme_slug = scheme_slug
        self.account_status = user_info['status']
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

    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.storage = self.get_pid_store()
        self.check_browser_availability()
        self.delay = 15
        self.scheme_id = user_info['scheme_account_id']
        self.scheme_slug = scheme_slug
        self.account_status = user_info['status']
        self.headers = {}
        self.retry_count = retry_count
        self.setup_browser(self.storage)

    @staticmethod
    def get_pid_store():
        storage = SeleniumPIDStore()
        storage.terminate_old_browsers()
        return storage

    def check_browser_availability(self):
        if not self.storage.is_browser_available():
            # Wait a random time to not create waves of load when all the browsers finish waiting
            time.sleep(randint(20, 40))
        if not self.storage.is_browser_available():
            raise AgentException(
                AgentError(RESOURCE_LIMIT_REACHED)
            )

    def setup_browser(self, pid_store):
        pass
    #     try:
    #         options = webdriver.firefox.options.Options()
    #         options.add_argument('--headless')
    #         options.add_argument('--hide-scrollbars')
    #         options.add_argument('--disable-gpu')
    #         self.browser = webdriver.Firefox(firefox_options=options, log_path='/dev/null')
    #         pid = self.browser.service.process.pid
    #         pid_store.set(pid)
    #         self.browser.implicitly_wait(self.delay)
    #     except Exception:
    #         self.close_selenium()
    #         raise
    #
    # def attempt_login(self, credentials):
    #     try:
    #         super().attempt_login(credentials)
    #     finally:
    #         self.close_selenium()

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
        try:
            pid = self.browser.service.process.pid
            self.browser.quit()
            self.storage.close_process_and_delete(str(pid))
        except (ProcessLookupError, AttributeError):
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
    """
    Base class for merchant API integrations.
    """

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None):
        self.retry_count = retry_count
        self.scheme_id = user_info['scheme_account_id']
        self.scheme_slug = scheme_slug
        self.user_info = user_info
        self.config = config
        self.identifier_type = ['barcode', 'card_number', 'merchant_scheme_id2']
        # used to map merchant identifiers to scheme credential types
        self.merchant_identifier_mapping = {
            'merchant_scheme_id2': 'merchant_identifier'
        }

        self.record_uid = None
        self.result = None

        # { error we raise: error we receive in merchant payload }
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
        account_link = self.user_info['status'] == SchemeAccountStatus.WALLET_ONLY

        self.record_uid = hash_ids.encode(self.scheme_id)
        handler_type = Configuration.VALIDATE_HANDLER if account_link else Configuration.UPDATE_HANDLER

        self.result = self._outbound_handler(credentials, self.scheme_slug, handler_type=handler_type)

        error = self.result.get('errors')
        if error:
            self._handle_errors(self.result['code'])

        # For adding the scheme account credential answer to db after first successful login or if they change.
        identifiers = self._get_identifiers(self.result)
        self.identifier = {}
        try:
            for key, value in identifiers.items():
                if credentials[key] != value:
                    self.identifier[key] = value
        except KeyError:
            self.identifier = identifiers

    def register(self, data, inbound=False):
        """
        Calls handler, passing in 'join' as the handler_type.
        :param data: user account credentials to register for merchant scheme or validated merchant response data
        for outbound or inbound processes respectively.
        :param inbound: Boolean for if the data should be handled for an inbound response or outbound request
        :return: None
        """
        if inbound:
            self._async_inbound(data, self.scheme_slug, handler_type=Configuration.JOIN_HANDLER)
        else:
            self.record_uid = data['record_uid'] = hash_ids.encode(self.scheme_id)

            self.result = self._outbound_handler(data, self.scheme_slug, handler_type=Configuration.JOIN_HANDLER)

            # Async joins will return empty 200 responses so there is nothing to process.
            if self.config.integration_service == 'SYNC':
                self.process_join_response()

    # Should be overridden in the agent if there is agent specific processing required for their response.
    def process_join_response(self):
        """
        Processes a merchant's response to a join request. On success, sets scheme account as ACTIVE and adds
        identifiers/scheme credential answers to database.
        :return: None
        """
        # check for error response
        error = self.result.get('errors')
        if error:
            self._handle_errors(self.result['code'])

        identifier = self._get_identifiers(self.result)
        update_pending_join_account(self.user_info['scheme_account_id'], "success", self.result['message_uid'],
                                    identifier=identifier)

        status = SchemeAccountStatus.ACTIVE
        publish.status(self.scheme_id, status, self.result['message_uid'])

    def _outbound_handler(self, data, scheme_slug, handler_type):
        """
        Handler service to apply merchant configuration and build JSON, for request to the merchant, and
        handles response. Configuration service is called to retrieve merchant config.
        :param data: python object data to be built into the JSON object.
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :param handler_type: type of handler to retrieve correct config e.g update, validate, join
        :return: dict of response data
        """
        message_uid = str(uuid1())
        if not self.config:
            self.config = Configuration(scheme_slug, handler_type)

        logger.setLevel(self.config.log_level)

        data['message_uid'] = message_uid
        data['record_uid'] = self.record_uid
        data['callback_url'] = self.config.callback_url

        merchant_scheme_ids = self.get_merchant_ids(data)
        data.update(merchant_scheme_ids)

        payload = json.dumps(data)

        # data without encrypted credentials for logging only
        temp_data = {k: v for k, v in data.items() if k not in ENCRYPTED_CREDENTIALS}

        logging_info = self._create_log_message(
            temp_data,
            message_uid,
            scheme_slug,
            handler_type,
            self.config.integration_service,
            "OUTBOUND"
        )

        logger.info(json.dumps(logging_info))

        response_json = self._sync_outbound(payload, self.config)

        response_data = {}
        if response_json:
            response_data = json.loads(response_json)

            logging_info['direction'] = "INBOUND"
            logging_info['json'] = response_data
            if response_data.get('errors'):
                logging_info['contains_errors'] = True
                logger.error(json.dumps(logging_info))
            else:
                logger.info(json.dumps(logging_info))

        return response_data

    def _inbound_handler(self, data, scheme_slug, handler_type):
        """
        Handler service for inbound response i.e. response from async join. The response json is logged,
        converted to a python object and passed to the relevant method for processing.
        :param data: dict of payload
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :param handler_type: type of handler (String). e.g 'join'
        :return: dict of response data
        """
        self.result = data

        logging_info = self._create_log_message(
            data,
            self.result.get('message_uid'),
            scheme_slug,
            handler_type,
            'ASYNC',
            'INBOUND'
        )

        if self.result.get('errors'):
            logging_info['contains_errors'] = True
            logger.error(json.dumps(logging_info))
        else:
            logger.info(json.dumps(logging_info))

        return self.process_join_response()

    def _sync_outbound(self, json_data, config):
        """
        Synchronous outbound service to build a request and make call to merchant endpoint.
        Calls are made to security and back off services pre-request.
        :param json_data: JSON string of payload to send to merchant
        :param config: dict of merchant configuration settings
        :return: Response payload
        """
        security_agent = get_security_agent(config.security_service, config.security_credentials)
        request = security_agent.encode(json_data)
        back_off_service = BackOffService()

        for retry_count in range(1 + config.retry_limit):
            if back_off_service.is_on_cooldown(config.scheme_slug, config.handler_type):
                response_json = create_error_response(errors[NOT_SENT]['code'], errors[NOT_SENT]['name'])
                break
            else:
                response = requests.post(config.merchant_url, **request)
                status = response.status_code

                if status == 200:
                    response_json = security_agent.decode(response.headers,
                                                          response.text)
                    # Log if request was redirected
                    if response.history:
                        logging_info = self._create_log_message(
                            response_json,
                            json.loads(json_data)['message_uid'],
                            config.scheme_slug,
                            config.handler_type,
                            config.integration_service,
                            "OUTBOUND"
                        )
                        logger.warning(json.dumps(logging_info))
                    break

                elif status in [503, 504, 408]:
                    response_json = create_error_response(errors[NOT_SENT]['code'], errors[NOT_SENT]['name'])
                else:
                    response_json = create_error_response(errors[UNKNOWN]['code'],
                                                          errors[UNKNOWN]['name'] + ' with status code {}'
                                                          .format(status))

                if retry_count == config.retry_limit:
                    back_off_service.activate_cooldown(config.scheme_slug, config.handler_type, BACK_OFF_COOLDOWN)

        return response_json

    def _async_inbound(self, data, scheme_slug, handler_type):
        """
        Asynchronous inbound service that will set logging level based on configuration per merchant and return
        a success response asynchronously before calling the inbound handler service.
        :param data: dict of validated merchant response data.
        :param scheme_slug: Bink's unique identifier for a merchant (slug)
        :param handler_type: Int. A choice from Configuration.HANDLER_TYPE_CHOICES
        :return: None
        """
        if not self.config:
            self.config = Configuration(scheme_slug, handler_type)
        logger.setLevel(self.config.log_level)

        self.record_uid = hash_ids.encode(self.scheme_id)

        # asynchronously call handler
        thread_pool_executor.submit(self._inbound_handler, data, self.scheme_slug, handler_type)

    # agents will override this if unique values are needed
    def get_merchant_ids(self, credentials):
        merchant_ids = {
            'merchant_scheme_id1': hash_ids.encode(self.user_info['user_id']),
            'merchant_scheme_id2': credentials.get('merchant_identifier'),
        }

        return merchant_ids

    def _handle_errors(self, response, exception_type=LoginError):
        for key, values in self.errors.items():
            if response in values:
                raise exception_type(key)
        raise AgentError(UNKNOWN)

    def _create_log_message(self, json_msg, msg_uid, scheme_slug, handler_type, integration_service, direction,
                            contains_errors=False):
        return {
            "json": json_msg,
            "message_uid": msg_uid,
            "record_uid": self.record_uid,
            "merchant_id": scheme_slug,
            "handler_type": handler_type,
            "integration_service": integration_service,
            "direction": direction,
            "expiry_date": arrow.utcnow().replace(days=+90).format('YYYY-MM-DD HH:mm:ss'),
            "contains_errors": contains_errors
        }

    def _get_identifiers(self, data):
        """Checks if data contains any identifiers (i.e barcode, card_number) and returns a dict with their values."""
        _identifier = {}
        for identifier in self.identifier_type:
            value = data.get(identifier)
            if value:
                converted_credential_type = self.merchant_identifier_mapping.get(identifier) or identifier
                _identifier[converted_credential_type] = value
        return _identifier
