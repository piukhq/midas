from decimal import Decimal

from app.utils import extract_decimal
from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED


class Marriott(SeleniumMiner):
    points = None
    is_login_successful = False

    def _check_if_logged_in(self):
        self.browser.implicitly_wait(5)
        if self.browser.find_elements_by_class_name('t-error-msg'):
            raise LoginError(STATUS_LOGIN_FAILED)
        self.browser.implicitly_wait(15)

        self.is_login_successful = True

    def login(self, credentials):
        self.browser.get('https://www.marriott.co.uk/Channels/rewards/signIn-uk.mi')
        self.browser.find_element_by_xpath('//input[@id="field-user-id"]').send_keys(credentials['email'])
        self.browser.find_element_by_xpath('//input[@id="field-password"]').send_keys(credentials['password'])
        self.browser.find_element_by_xpath('//div[@id="layout-body"]/form/div/div/div/button').click()

        self._check_if_logged_in()

        points_parent_element = self.browser.find_element_by_id('header-rewards-panel-trigger')
        points_element = points_parent_element.find_element_by_class_name('t-header-subtext')
        self.points = extract_decimal(points_element.text)

    def balance(self):
        return {
            'points': self.points,
            'value': Decimal('0'),
            'value_label': ''
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
