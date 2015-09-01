import hashlib
from robobrowser import RoboBrowser
from urllib.parse import urlsplit
from app.utils import open_browser
from app.agents.exceptions import MinerError, LoginError


class Miner(object):
    retry_limit = 2

    def __init__(self, retry_count):
        self.browser = RoboBrowser(parser="lxml", history=False)
        self.retry_count = retry_count

    def attempt_login(self, credentials):
        if self.retry_count <= self.retry_limit:
            self.login(credentials)
        else:
            raise MinerError("RETRY_LIMIT_REACHED")

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
        except self.browser.response.exceptions.HTTPError as e:
            raise MinerError('AGENT_DOWN') from e

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
        s = "{0}{1}{2}".format(transaction['date'], transaction['title'], transaction['points'])
        transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()
        return transaction

    def path_error_check(self, incorrect_path, error_selector, error_causes):
        """
        Given a path the browser shouldn't be on test for a list of error messages.
        Raise the appropriate error.
        """
        if urlsplit(self.browser.url).path == incorrect_path:
            message = self.browser.select(error_selector)

            for error in error_causes:
                error_name, error_match = error
                if message and message[0].contents[0].strip().startswith(error_match):
                    raise LoginError(error_name)
            raise LoginError('UNKNOWN')

    def view(self):
        """
        Open the RoboBrowser object in a browser in its current state
        """
        parts = urlsplit(self.browser.url)
        base_href = "{0}://{1}".format(parts.scheme, parts.netloc)
        open_browser(self.browser.parsed.prettify("utf-8"), base_href)