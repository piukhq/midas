from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
import arrow
from selenium.common.exceptions import TimeoutException


class MalaysiaAirlines(SeleniumMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        self.wait_for_page_load()
        try:
            username = self.browser.find_element_by_class_name('username')
            self.wait_for_element_to_be_visible(username, timeout=15)
            self.is_login_successful = True
        except TimeoutException:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.browser.get('https://www.malaysiaairlines.com/enrich-portal/login.html')
        self.wait_for_page_load()
        self.browser.find_element_by_name('mhNumber').send_keys(credentials['card_number'])
        self.browser.find_elements_by_name('Password')[3].send_keys(credentials['password'])
        self.browser.find_element_by_class_name('login-form').click()

    def login(self, credentials):
        # website can be very slow
        self.browser.implicitly_wait(60)
        try:
            self._login(credentials)
        except:
            raise LoginError(UNKNOWN)

        self._check_if_logged_in()
        self.points = self.browser.find_element_by_class_name('miles-value').text
        self.transaction_list = self.browser.find_elements_by_class_name('miles-table tbody tr')

    def balance(self):

        return {
            'points': extract_decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        date = row.find_element_by_class_name('date').text
        description = row.find_element_by_class_name('activity').text
        points = row.find_element_by_class_name('earn').text

        return {
            'date': arrow.get(date, 'DD MMM YYYY'),
            'description': description,
            'points': Decimal(points)
        }

    def scrape_transactions(self):
        return self.transaction_list
