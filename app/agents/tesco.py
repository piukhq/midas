from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, STATUS_ACCOUNT_LOCKED
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
                      "?from=https%3a%2f%2fsecure.tesco.com%2fclubcard%2fmyaccount%2falpha443%2fhome")

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

    @staticmethod
    def get_card_number(barcode):
        return '634004' + barcode[4:]

    def balance(self):
        points = extract_decimal(self.browser.select("#pointsTotal")[0].contents[0].strip())
        value = self.calculate_point_value(points)

        balance_field = self.browser.select("#vouchersTotal")

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
        self.open_url("https://secure.tesco.com/Clubcard/MyAccount/Alpha443/Points/PointsDetail?period=current")
        return self.browser.select(
            '#page-body > div > div > div.l-column.padded-left > div > div > form > table > tbody > tr')
