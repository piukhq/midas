from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from decimal import Decimal
import re


class HollandAndBarrett(Miner):
    point_value_re = re.compile("^You've collected (\d+) points so far this quarter which will be worth £(\d*\.\d\d)")
    balance_re = re.compile('^You also have   £(\d*\.\d\d) worth of vouchers waiting to be spent')

    def login(self, credentials):
        self.open_url('https://www.hollandandbarrett.com/my-account/login.jsp?myaccount=true')

        login_form = self.browser.get_form(action='/my-account/login.jsp?_DARGS=/my-account/login.jsp')
        login_form['email'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error('/my-account/login.jsp',
                         (('.form-errors > ul', STATUS_LOGIN_FAILED, 'Please enter valid email address'),))

    def balance(self):
        info_box = self.browser.select('section.s-account-module.rfl-summary > div > div > h3')[0]
        point_text = info_box.contents[0].strip()
        value_text = info_box.contents[3].strip()

        points, value = self.point_value_re.findall(point_text)[0]
        balance = self.balance_re.findall(value_text)[0]

        return {
            'points': Decimal(points),
            'value': Decimal(value),
            'value_label': '£{}'.format(value),
            'balance': Decimal(balance),
        }

    def transactions(self):
        return None