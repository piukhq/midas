from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
from selenium.common.exceptions import TimeoutException


class Qantas(SeleniumMiner):
    async = True

    def check_if_logged_in(self):
        try:
            self.wait_for_value('.login-ribbon__details', 'points')
            self.points = self.browser.find_element_by_class_name('login-ribbon__details').text
            self.is_login_successful = True

        except TimeoutException:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.browser.get('https://www.qantas.com/gb/en/frequent-flyer/log-in.html')
        form = self.browser.find_element_by_name('LSLLoginForm')
        self.browser.find_element_by_css_selector('.login-ribbon button').click()
        self.browser.find_element_by_name('memberId').send_keys(credentials['card_number'])
        self.browser.find_element_by_name('lastName').send_keys(credentials['last_name'])
        self.browser.find_element_by_name('memberPin').send_keys(credentials['pin'])
        form.find_element_by_css_selector("button[type='submit']").click()

    def login(self, credentials):
        try:
            self._login(credentials)
        except Exception:
            raise LoginError(UNKNOWN)

        self.check_if_logged_in()

    def balance(self):

        return {
            'points': extract_decimal(self.points),
            'value': Decimal(0),
            'value_label': ''
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
