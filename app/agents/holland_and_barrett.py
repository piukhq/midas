import re
from decimal import Decimal

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_ACCOUNT_LOCKED, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class HollandAndBarrett(RoboBrowserMiner):
    point_value_re = re.compile(
        "^You've collected (\d+) points so far this quarter(?:\.| which will be worth £(\d*\.\d\d))")
    balance_re = re.compile('<[^>]+>')

    def login(self, credentials):
        self.browser.open('https://www.hollandandbarrett.com/my-account/login.jsp?myaccount=true',
                          verify=self.get_requests_cacert())

        login_form = self.browser.get_form(action='/my-account/login.jsp?_DARGS=/my-account/login.jsp')
        login_form['email'].value = credentials['email']
        login_form['password'].value = credentials['password']
        submit_field = login_form.submit_fields['/atg/userprofiling/ProfileFormHandler.login']

        self.browser.submit_form(login_form, submit=submit_field)

        self.check_error('/my-account/login.jsp', (('.form-errors > ul', STATUS_LOGIN_FAILED,
                                                    'Please enter valid email address'),))

        self.check_error('/defaultPage.jsp', (('body', STATUS_ACCOUNT_LOCKED,
                                               'Your session expired due to inactivity.'),))

    def balance(self):
        info_box = self.browser.select('section.s-account-module.rfl-summary > div > div > h3')[0]
        point_text = info_box.contents[0].strip()
        value_text = str(info_box.contents[3].strip())
        value_text = re.sub(self.balance_re, '', value_text)

        points, value = self.point_value_re.findall(point_text)[0]

        if not value:
            value = '0.00'

        if value_text == 'You have no Cash Vouchers available.':
            balance = '0'
        else:
            balance = extract_decimal(value_text)

        return {
            'points': Decimal(points),
            'value': Decimal(value),
            'value_label': '£{}'.format(value),
            'balance': Decimal(balance),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
