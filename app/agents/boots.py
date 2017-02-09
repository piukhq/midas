import arrow

from app.agents.base import Miner
from app.agents.exceptions import STATUS_ACCOUNT_LOCKED, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Boots(Miner):
    def login(self, credentials):
        self.open_url('http://www.boots.com/LogonForm?catalogId=28501&myAcctMain=1&langId=-1&storeId=11352')

        login_form = self.browser.get_form('Logon')
        login_form['logonId'].value = credentials['email']
        login_form['logonPassword'].value = credentials['password']

        self.browser.submit_form(login_form)

        sel = 'p.overlay_head'
        self.check_error('/webapp/wcs/stores/servlet/Logon', (
                         (sel, STATUS_ACCOUNT_LOCKED,
                          'Account locked'), ))

        sel = 'a[href*="logonError"]'
        self.check_error('/webapp/wcs/stores/servlet/Logon', (
                         (sel, STATUS_LOGIN_FAILED,
                          'The email address and/or password you entered has not been recognised.'), ))

    def balance(self):
        elements = self.browser.select("p#advantageCardDetails")
        spans = elements[0].select("span")
        true_points = extract_decimal(spans[0].text)
        true_value = extract_decimal(spans[1].text)

        return {
            'points': true_points,
            'value': true_value,
            'value_label': '£{}'.format(true_value)
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")

        return {
            "date": arrow.get(items[0].contents[0], 'DD/MM/YYYY'),
            "description": items[1].contents[0],
            "points": extract_decimal(items[3].contents[0]),
        }

    def scrape_transactions(self):
        self.open_url('https://www.boots.com/ADCAccountSummary')
        return self.browser.select("#adcardPointStatement tr")[1:]
