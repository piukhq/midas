from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class Toysrus(RoboBrowserMiner):
    def login(self, credentials):
        url = 'https://club.toysrus.co.uk'
        self.open_url(url)

        login_form = self.browser.get_form('form1')
        login_form['ctl00$bodyPlaceHolder$emailTextBox'].value = credentials['email']
        login_form['ctl00$bodyPlaceHolder$passwordTextBox'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = '#bodyPlaceHolder_errboxLabel'
        self.check_error('/', ((selector, STATUS_LOGIN_FAILED, "Please fill out"),))

    def balance(self):
        self.open_url('https://club.toysrus.co.uk/Account_PointsTotal.aspx')
        point_holder = self.browser.select('#bodyPlaceHolder_ansTotalPoints')[0]
        return {
            'points': extract_decimal(point_holder.text),
            'value': Decimal('0'),
            'value_label': '',
        }

    def scrape_transactions(self):
        return None
