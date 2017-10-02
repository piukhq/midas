from app.agents.base import Miner
from app.agents.exceptions import LoginError, TRIPPED_CAPTCHA, STATUS_LOGIN_FAILED
from decimal import Decimal, ROUND_DOWN
import arrow


class PapaJohns(Miner):
    point_conversion_rate = Decimal('0.04')

    def login(self, credentials):
        self.open_url('http://www.papajohns.co.uk/')

        form = self.browser.get_form('aspnetForm')
        form['__EVENTTARGET'].value = 'ctl00$_objHeader$lbLoginRegisterItem'
        form['__EVENTARGUMENT'].value = ''
        self.browser.submit_form(form)

        form = self.browser.get_form('aspnetForm')

        if 'ctl00$_objHeader$txtEmail1' not in form.fields:
            raise LoginError(TRIPPED_CAPTCHA)

        form['ctl00$_objHeader$txtEmail1'].value = credentials['email']
        form['ctl00$_objHeader$txtPassword'].value = credentials['password']
        form['__EVENTTARGET'].value = 'ctl00$_objHeader$lbSignIn'
        form['__EVENTARGUMENT'].value = ''
        self.browser.submit_form(form)

        self.open_url('https://www.papajohns.co.uk/my-papa-rewards.aspx')
        if self.browser.url != 'https://www.papajohns.co.uk/my-papa-rewards.aspx':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points = Decimal(self.browser.select('#ctl00_cphBody_rptPoints_ctl00_lblPointsTotal')[0].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)
        reward = self.format_label(value, 'free pizza')
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': reward,
        }

    def parse_transaction(self, row):
        return {
            'date': arrow.get(row.contents[1].text.strip(), 'DD-MMM-YYYY'),
            'description': row.contents[3].text.strip(),
            'points': Decimal(row.contents[5].text.strip()),
        }

    def scrape_transactions(self):
        return self.browser.select('table.nutritionalTable > tbody > tr')[2:]
