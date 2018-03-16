import arrow
from decimal import Decimal

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import (LoginError, RegistrationError, STATUS_LOGIN_FAILED, STATUS_REGISTRATION_FAILED,
                                   ACCOUNT_ALREADY_EXISTS)


class TKMaxx(RoboBrowserMiner):
    is_login_successful = False
    is_registration_completed = False

    def check_if_registration_completed(self):
        success_element = self.browser.select('.intro')[0].text
        if success_element.startswith('You have completed your registration for Treasure'):
            self.is_registration_completed = True
        else:
            error_message = self.browser.select('.alert')[0].text
            if 'We already have an account for that email' in error_message:
                raise RegistrationError(ACCOUNT_ALREADY_EXISTS)

            raise RegistrationError(STATUS_REGISTRATION_FAILED)

    def check_if_logged_in(self):
        self.browser.open('https://www.bigbrandtreasure.com/en/user/')

        current_url = self.browser.url
        login_fail_url = 'https://www.bigbrandtreasure.com/en/login'
        if current_url != login_fail_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _register(self, credentials):
        self.browser.open('https://www.bigbrandtreasure.com/en/user/logout')
        self.browser.open('https://www.bigbrandtreasure.com/en/store/autocomplete/en?q=Slough')

        store_info = self.browser.response.json()[0]
        store_id = store_info['value']
        store_label = store_info['label']

        url = 'https://www.bigbrandtreasure.com/en/user/register'
        self.browser.open(url)
        register_form = self.browser.get_form('user-register-form')

        if not credentials['title'][-1:] == '.':
            credentials['title'] += '.'

        title_options = register_form['field_user_title'].options
        title_index = title_options.index(credentials['title'])

        country_options = register_form['preferred_langcode'].options
        country_index = country_options.index('en')

        register_form['field_user_title'] = title_options[title_index]
        register_form['field_first_name[0][value]'] = credentials['first_name']
        register_form['field_last_name[0][value]'] = credentials['surname']
        register_form['dob_date'] = credentials['date_of_birth']
        register_form['zip'] = credentials['postcode']
        register_form['store_id'] = store_id
        register_form['store_ie'] = ''
        register_form['store_en'] = store_label
        register_form['mail'] = credentials['email']
        register_form['email_confirm'] = credentials['email']
        register_form['pass[pass1]'] = credentials['password']
        register_form['pass[pass2]'] = credentials['password']
        register_form['card_number'] = credentials['card_number']
        register_form['preferred_langcode'] = country_options[country_index]
        register_form['sign_prize_draw'] = register_form['sign_prize_draw'].options[0]

        self.browser.submit_form(register_form)

    def register(self, credentials):
        self._register(credentials)
        self.check_if_registration_completed()

        return {"message": "success"}

    def set_headers(self):
        self.headers['Host'] = 'www.bigbrandtreasure.com'
        self.headers['Origin'] = 'https://www.bigbrandtreasure.com'
        self.headers['Referer'] = 'https://www.bigbrandtreasure.com/en/login'
        self.headers['Content-Type'] = 'application/x-www-form-urlencoded'

    def _login(self, credentials):
        self.open_url('https://www.bigbrandtreasure.com/en/login')

        self.set_headers()

        login_form = self.browser.get_form('user-login-form')
        login_form['name'].value = credentials['email']
        login_form['pass'].value = credentials['password']
        self.browser.submit_form(login_form)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        self.browser.open('https://www.bigbrandtreasure.com/en/reward')
        points = self.browser.select('.shops p em')[1].text

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        row = row.split('\n')
        return {
            'date': arrow.get(row[0], 'DD MMM YYYY'),
            'description': "{}, Items: {}".format(row[1], row[2]),
            'points': Decimal(1)
        }

    def scrape_transactions(self):
        self.open_url('https://www.bigbrandtreasure.com/en/transactions')
        transactions = self.browser.select('.transactions > .mobileswrap > ul')
        return [
            row.text.strip()
            for row in transactions
            if row.text != '\nDate\nStore\nItems\n'
        ]
