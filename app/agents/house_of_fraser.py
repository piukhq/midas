from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
from time import sleep
from selenium.common.exceptions import NoSuchElementException


class HouseOfFraser(SeleniumMiner):
    point_conversion_rate = Decimal('0.01')

    def _login(self, credentials):
        self.browser.get('https://www.houseoffraser.co.uk/account/login/checkuserexists')
        self.browser.find_element_by_css_selector('#email').send_keys(credentials['email'])
        self.browser.find_element_by_css_selector('#js-login-password').send_keys(credentials['password'])
        self.browser.find_element_by_css_selector('#js-signin-submit').click()
        sleep(5)

    def _check(self):
        if self.browser.current_url == "https://www.houseoffraser.co.uk/":
            self.is_successful_login = True
        else:
            sleep(10)
            self.browser.implicitly_wait(10)
            try:
                incorrect_password = self.browser.find_element_by_css_selector('#js-login-password-error').text
            except NoSuchElementException:
                incorrect_password = None
            try:
                incorrect_credentials = self.browser.find_element_by_css_selector(
                    '[data-bind="text: ErrorMessage"]').text
            except NoSuchElementException:
                incorrect_credentials = None
            if incorrect_password or incorrect_credentials:
                raise LoginError(STATUS_LOGIN_FAILED)

            raise LoginError(UNKNOWN)

    def login(self, credentials):
        self._login(credentials=credentials)
        self._check()
        self.get_balance()

    def get_balance(self):
        self.browser.get('https://www.houseoffraser.co.uk/recognition/recognitionsummary')
        sleep(5)
        points = self.browser.find_element_by_css_selector('[data-bind="text: PointBalance()"]').text
        self.points = extract_decimal(points)
        self.value = self.calculate_point_value(self.points)
        self.balance_value = self.browser.find_element_by_css_selector('[data-bind="text: RewardsBalance()"]').text

    def balance(self):
        return {
            'points': self.points,
            'value': self.value,
            'value_label': '£{}'.format(self.value),
            'balance': extract_decimal(self.balance_value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
