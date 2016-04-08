from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED
from decimal import Decimal
import arrow
import re


class HollandAndBarrett(Miner):
    point_value_re = re.compile("^You've collected (\d+) points so far this quarter which will be worth £(\d*\.\d\d)")
    balance_re = re.compile('^You also have   £(\d*\.\d\d) worth of vouchers waiting to be spent')

    def login(self, credentials):
        self.open_url('https://www.hollandandbarrett.com/my-account/login.jsp?myaccount=true', verify=False)

        login_form = self.browser.get_form(action='/my-account/login.jsp?_DARGS=/my-account/login.jsp')
        login_form['email'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form, verify=False)

        self.check_error('/my-account/login.jsp',
                         (('.form-errors > ul', STATUS_LOGIN_FAILED, 'Please enter valid email address'),))

        self.check_error('/defaultPage.jsp',
                         (('body', STATUS_ACCOUNT_LOCKED, 'Your session expired due to inactivity.'),))

    def balance(self):
        info_box = self.browser.select('section.s-account-module.rfl-summary > div > div > h3')[0]
        point_text = info_box.contents[0].strip()
        value_text = info_box.contents[3].strip()

        points, value = self.point_value_re.findall(point_text)[0]

        if value_text == 'You have no Cash Vouchers available.':
            balance = '0'
        else:
            balance = self.balance_re.findall(value_text)[0]

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
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
