from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, AgentError, STATUS_LOGIN_FAILED, UNKNOWN, END_SITE_DOWN
from app.utils import extract_decimal
from decimal import Decimal
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class IberiaPlus(SeleniumMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        try:
            with self.wait_for_page_load():
                self.points = self.browser.find_element_by_css_selector('#member-log li:nth-child(2)').text
            self.is_login_successful = True

        except NoSuchElementException:
            raise LoginError(STATUS_LOGIN_FAILED)
        except TimeoutException:
            raise AgentError(END_SITE_DOWN)

    def _login(self, credentials):
        self.browser.get('https://www.iberia.com/web/obsmenu.do?menuId=IBMIBP')
        form = self.browser.find_element_by_name('loginFormTop')
        self.browser.find_element_by_class_name('login').click()
        self.browser.find_element_by_name('username').send_keys(credentials['card-number'])
        self.browser.find_element_by_name('password').send_keys(credentials['password'])
        form.find_element_by_css_selector('input[type="submit"]').click()

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
