from decimal import Decimal, ROUND_DOWN

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, TRIPPED_CAPTCHA, STATUS_LOGIN_FAILED, UNKNOWN


class PapaJohns(RoboBrowserMiner):
    point_conversion_rate = Decimal('0.04')
    is_login_successful = False

    def get_sign_in_form(self):
        self.open_url('https://www.papajohns.co.uk/')

        form = self.browser.get_form('aspnetForm')
        form['__EVENTTARGET'].value = 'ctl00$_objHeader$lbLoginRegisterItem'
        form['__EVENTARGUMENT'].value = ''
        self.browser.submit_form(form)

    def _login(self, credentials):
        form = self.browser.get_form()
        if 'ctl00$_objHeader$txtEmail1' not in form.fields:
            raise LoginError(TRIPPED_CAPTCHA)

        form['ctl00$_objHeader$txtEmail1'].value = credentials['email']
        form['ctl00$_objHeader$txtPassword'].value = credentials['password']
        form['__EVENTTARGET'].value = 'ctl00$_objHeader$lbSignIn'
        form['__EVENTARGUMENT'].value = ''
        self.browser.submit_form(form)

    def _check_if_logged_in(self):
        rewards_url = 'https://www.papajohns.co.uk/my-papa-rewards.aspx'
        try:
            self.open_url(rewards_url)
            current_url = self.browser.url
            if current_url == rewards_url:
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def login(self, credentials):
        try:
            self.get_sign_in_form()
            self._login(credentials=credentials)
        except:
            raise LoginError(UNKNOWN)

        self._check_if_logged_in()

    def balance(self):
        points = Decimal(self.browser.select('#ctl00_cphBody_rptPoints_ctl00_lblPointsTotal')[0].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)
        reward = self.format_label(value, 'free pizza')
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row.contents[1].text.strip(), 'DD-MMM-YYYY'),
            'description': row.contents[3].text.strip(),
            'points': Decimal(row.contents[5].text.strip()),
        }

    def scrape_transactions(self):
        return self.browser.select('table.nutritionalTable > tbody > tr')[2:]
