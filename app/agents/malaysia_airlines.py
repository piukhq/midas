from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
from time import sleep


class MalaysiaAirlines(SeleniumMiner):

    def check_if_logged_in(self):
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
        self.browser.find_element_by_name('mhNumber').send_keys(credentials['card_number'])
        sleep(5)
        self.browser.find_elements_by_name('Password')[2].send_keys(credentials['password'])
        sleep(5)
        self.browser.find_element_by_class_name('login-form').click()
        sleep(60)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

        self.points = self.browser.find_element_by_class_name('miles-value').text
        self.get_transactions()

    def balance(self):
        return {
            'points': extract_decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
        }

    def get_transactions(self):
        transaction_list = self.browser.find_elements_by_class_name('miles-table tbody tr')
        self.sorted_transactions = []
        for transaction in transaction_list:
            transaction_dict = {
                'date': transaction.find_element_by_class_name('date').text,
                'description': transaction.find_element_by_class_name('activity').text,
                'points': transaction.find_element_by_class_name('earn').text
            }
            self.transactions.append(transaction_dict)

    @staticmethod
    def parse_transaction(row):

        return {
            'date': arrow.get(row['date'], 'DD MMM YYYY'),
            'description': row['description'],
            'points': Decimal(row['points'])
        }

    def scrape_transactions(self):
        return self.sorted_transactions
