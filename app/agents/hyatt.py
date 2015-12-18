from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, END_SITE_DOWN
from app.utils import extract_decimal
from decimal import Decimal


class Hyatt(Miner):
    def login(self, credentials):
        self.open_url('https://www.hyatt.com/gp/en/index.jsp')

        error_message = self.browser.select('#hyattBuilt_pgctntClmnQuickBookAndSearchModuleHolder > div > div > p')
        mtce_text = 'The Hyatt Gold Passport system is undergoing maintenance at this time.'
        if error_message and error_message[0].text.strip() == mtce_text:
            raise LoginError(END_SITE_DOWN)

        login_form = self.browser.get_form('signin')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        if self.browser.response.status_code == 403:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        selector = '#hyattBuilt_pgctntClmnQuickBookAndSearchModuleHolder > div > div > form > div > span.hbDefinition'
        points = self.browser.select(selector)

        return {
            'points': extract_decimal(points[0].text),
            'value': Decimal('0'),
            'value_label': '',
        }

    def scrape_transactions(self):
        return None
