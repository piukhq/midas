from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal
import arrow
from time import sleep

class MalaysiaAirlines(SeleniumMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        try:
            username = self.browser.find_element_by_class_name('username')
            if username.is_displayed():
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def _login(self, credentials):
        self.browser.get('https://www.malaysiaairlines.com/enrich-portal/login.html')
        sleep(5)
        self.browser.find_element_by_name('mhNumber').\
            send_keys(credentials['card_number'])
        sleep(5)
        self.browser.find_elements_by_name('Password')[3].\
            send_keys(credentials['password'])
        sleep(5)
        self.browser.find_element_by_class_name('login-form').click()
        sleep(60)

    def login(self, credentials):
        self.browser.implicitly_wait(60)
        try:
            self._login(credentials)
        except:
            raise LoginError(UNKNOWN)
        self._check_if_logged_in()

        self.points = self.browser.find_element_by_class_name('miles-value').text

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
        return self.browser.find_elements_by_class_name('miles-table'
                                                           ' tbody tr')