from app.agents.base import Miner
from app.agents.exceptions import (STATUS_LOGIN_FAILED, LoginError)
from app.utils import extract_decimal
from decimal import Decimal
import arrow
import re


class Tesco(Miner):
    is_login_successful = False
    point_conversion_rate = Decimal('0.01')
    transaction_id_regex = re.compile('\d{3}$')

    def _check_if_logged_in(self):
        current_url = self.browser.url
        correct_url = 'https://secure.tesco.com/clubcard' \
                      '/myaccount/home/home'

        if current_url == correct_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):

        self.open_url('https://secure.tesco.com/account/en-GB/login'
                      '?from=https://secure.tesco.com/Clubcard/'
                      'MyAccount/Alpha443/Points/Home')

        signup_form = self.browser.get_form(id='sign-in-form')
        signup_form['username'].value = credentials['email']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        self.open_url('https://secure.tesco.com/clubcard/myaccount/home/home')
        self._check_if_logged_in()

    def balance(self):
        points = extract_decimal(self.browser.select('.ddl-no-wrap')[1].text)
        value = self.calculate_point_value(points)
        balance = Decimal(self.get_vouchers_value())

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
            'balance': balance
        }

    def get_vouchers_value(self):
        self.headers['Host'] = "secure.tesco.com"
        self.headers['Referer'] = "https://secure.tesco.com/" \
                                  "Clubcard/MyAccount/Home/Home"
        self.headers['ADRUM'] = "isAjax:true"
        self.headers['X-Requested-With'] = "XMLHttpRequest"

        self.open_url('https://secure.tesco.com/Clubcard/'
                      'MyAccount/Vouchers/AvailableVouchers?{}')

        return self.browser.response.json()['count']

    @staticmethod
    def parse_transaction(row):
        items = row.find_all('td')
        return {
            'date': arrow.get(items[1].contents[0].strip(), 'DD/MM/YYYY'),
            'description': items[2].contents[0].strip(),
            'points': extract_decimal(items[4].contents[0].strip()),
        }

    def scrape_transactions(self):
        all_transaction_rows = []

        self.headers['Host'] = "secure.tesco.com"
        self.headers['Referer'] = "https://secure.tesco.com/" \
                                  "Clubcard/MyAccount/Points/Home"

        transactions = self.get_transactions_url()

        for transaction in transactions:
            transaction_rows = self.get_transaction_rows(transaction)

            for transaction_row in transaction_rows:
                all_transaction_rows.append(transaction_row)

        return all_transaction_rows

    def get_transactions_url(self):
        all_transactions_urls = []
        domain = 'https://secure.tesco.com'

        self.open_url('https://secure.tesco.com/Clubcard/'
                      'MyAccount/Points/Home')

        current_transaction = self.browser.select('#tbl_collectionperioddtls'
                                                  ' tr #lblPointdtlsview')[0]
        all_transactions = self.browser.select('#tbl_collectionperioddtls'
                                               ' tr #lblPointdtlsview')[1:]

        all_transactions.append(current_transaction)

        for transaction in all_transactions:
            transaction_url = domain + transaction['href']
            all_transactions_urls.append(transaction_url)

        return all_transactions_urls

    def get_transaction_rows(self, transaction_url):
        self.open_url(transaction_url)

        return self.browser.select('div.table-wrapper > form > table >'
                                   ' tbody > tr')
