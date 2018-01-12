from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
from selenium.common.exceptions import TimeoutException


class HouseOfFraser(SeleniumMiner):
    point_conversion_rate = Decimal('0.01')
    is_successful_login = None

    def _login(self, credentials):
        self.browser.get('https://www.houseoffraser.co.uk/account/login/checkuserexists')
        self.browser.find_element_by_css_selector('#email').send_keys(credentials['email'])
        self.browser.find_element_by_css_selector('#js-login-password').send_keys(credentials['password'])
        self.browser.find_element_by_css_selector('#js-signin-submit').click()

    def _check(self):
        try:
            self.wait_for_value('[data-bind="click: Logout"]', '', timeout=5)
            self.is_successful_login = True
        except TimeoutException:
            self.is_successful_login = False
            self.browser.implicitly_wait(1)
            incorrect_password = self.browser.find_elements_by_css_selector('#js-login-password-error')
            incorrect_credentials = self.browser.find_elements_by_css_selector('[data-bind="text: ErrorMessage"]')

            if incorrect_password or incorrect_credentials:
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def login(self, credentials):
        try:
            self._login(credentials=credentials)
        except Exception:
            self.is_successful_login = False
            raise LoginError(UNKNOWN)

        self._check()

        self.browser.get('https://www.houseoffraser.co.uk/recognition/recognitionsummary')
        self.wait_for_page_load()
        points = self.browser.find_element_by_css_selector('[data-bind="text: PointBalance()"]').text
        self.points_value = extract_decimal(points)
        self.value = self.calculate_point_value(self.points_value)
        self.balance_value = self.browser.find_element_by_css_selector('[data-bind="text: RewardsBalance()"]').text

    def balance(self):

        return {
            'points': self.points_value,
            'value': self.value,
            'value_label': '£{}'.format(self.value),
            'balance': extract_decimal(self.balance_value)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
