import hashlib
from requests import HTTPError
from robobrowser import RoboBrowser
from urllib.parse import urlsplit
from app.utils import open_browser
from app.agents.exceptions import MinerError, LoginError, AGENT_DOWN, UNKNOWN, RETRY_LIMIT_REACHED


class Miner(object):
    retry_limit = 2

    def __init__(self, retry_count):
        self.browser = RoboBrowser(parser="lxml", user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) "
                                                             "Gecko/20100101 Firefox/40.0")
        self.retry_count = retry_count

    def attempt_login(self, credentials):
        if self.retry_count <= self.retry_limit:
            self.login(credentials)
        else:
            raise MinerError(RETRY_LIMIT_REACHED)

    def open_url(self, url):
        """
        Sensible defaults and error handling for opening url
        http://www.mobify.com/blog/http-requests-are-hard/
        """
        connect_timeout = 1
        read_timeout = 5

        self.browser.open(url, timeout=(connect_timeout, read_timeout))

        try:
            self.browser.response.raise_for_status()
        except HTTPError as e:
            raise MinerError(AGENT_DOWN) from e

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def transactions(self):
        raise NotImplementedError()

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def hashed_transaction(self, transaction):
        transaction = self.parse_transaction(transaction)
        s = "{0}{1}{2}".format(transaction['date'], transaction['description'], transaction['points'])
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