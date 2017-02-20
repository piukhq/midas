from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, INVALID_MFA_INFO, LoginError, STATUS_ACCOUNT_LOCKED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
import json
import re

# TODO: add STATUS_ACCOUNT_LOCKED


class Tesco(Miner):
    retry_limit = 3
    point_conversion_rate = Decimal('0.01')

    mfa_digit_regex = re.compile('Please enter (\d+).*? digit')

    def login(self, credentials):
        self.open_url("https://secure.tesco.com/account/en-GB/login"
                      "?from=https://secure.tesco.com/Clubcard/MyAccount/Alpha443/Points/Home")

        signup_form = self.browser.get_form(id='sign-in-form')
        signup_form['username'].value = credentials['email']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        result_json_element = self.browser.select('#initial-data')
        if result_json_element:
            result_json = json.loads(result_json_element[0].contents[0])
            if 'accountLocked' in result_json and result_json['accountLocked']:
                raise LoginError(STATUS_ACCOUNT_LOCKED)

        selector = 'p.ui-component__notice__error-text'
        url = '/account/en-GB/login'
        self.check_error(url, ((selector, STATUS_LOGIN_FAILED, 'Unfortunately we do not recognise'),))

        if 'card_number' not in credentials:
            self.card_number = self.get_card_number(credentials['barcode'])
        else:
            self.card_number = credentials['card_number']
        self.do_mfa_login()

        self.open_url('https://secure.tesco.com/clubcard/myaccount/alpha443/points/home')

    def do_mfa_login(self):
        digit_form = self.browser.get_form()

        fields = self.browser.select('form.form.cf > fieldset > div.security')
        for field in fields:
            label_text = field.select('label')[0].text.strip()
            digit_index = int(self.mfa_digit_regex.match(label_text).group(1))

            input_name = field.select('input')[1].attrs['name']
            digit_form[input_name].value = self.card_number[digit_index - 1]

        self.browser.submit_form(digit_form)

        self.check_error("/Clubcard/MyAccount/Alpha443/Account/SecurityHome",
                         (("#errMsgHead", INVALID_MFA_INFO, "The details you have entered do not"), ))

    @staticmethod
    def get_card_number(barcode):
        return '634004' + barcode[4:]

    def balance(self):
        points = extract_decimal(self.browser.select("#pointsTotal")[0].contents[0].strip())
        value = self.calculate_point_value(points)

        balance_field = self.browser.select("#ltrCurrofferVuchers")

        if len(balance_field) > 0:
            balance = extract_decimal(balance_field[0].contents[0].strip())
        else:
            balance = Decimal('0')

        return {
            "points": points,
            'value': value,
            'value_label': '£{}'.format(value),
            'balance': balance
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[1].contents[0].strip(), 'DD/MM/YYYY'),
            "description": items[2].contents[0].strip(),
            "points": extract_decimal(items[4].contents[0].strip()),
        }

    def scrape_transactions(self):
        self.open_url('https://secure.tesco.com/Clubcard/MyAccount/Alpha443/Points/Home')

        # check if there's a security layer
        if self.browser.url.startswith("https://secure.tesco.com/Clubcard/MyAccount/Alpha443/Account/SecurityHome"):
            self.do_mfa_login()

        self.open_url('https://secure.tesco.com/Clubcard/MyAccount/Alpha443/Points/Home')

        current_transactions_link = self.browser.select('#tbl_collectionperioddtls > tbody > tr > td')[2].select('a')[0]
        self.browser.follow_link(current_transactions_link)

        return self.browser.select(
            '#page-body > div > div > div.l-column.padded-left > div > div > form > table > tbody > tr')
