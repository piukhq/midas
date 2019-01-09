from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
import json


class MalaysiaAirlines(RoboBrowserMiner):
    def check_if_logged_in(self):
        if self.browser.response.json()['responseCode'] == 'OK':
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        form = 'https://www.malaysiaairlines.com/bin/services/new/authuser'
        self.open_url(
            form,
            method='post',
            data={
                'userId': credentials['card_number'],
                'password': credentials['password']
            },
            headers={'Referer': 'https://www.malaysiaairlines.com/uk/en.html'})
        self.check_if_logged_in()

    def balance(self):
        phantom_cookie = self.browser.response.json()['phantomCookieValue']
        data = json.loads(phantom_cookie)
        return {
            'points': extract_decimal(data['milesCount']),
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
