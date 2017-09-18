from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from decimal import Decimal


class AirAsia(RoboBrowserMiner):
    def login(self, credentials):
        self.connect_timeout = 3
        self.open_url('https://member.airasia.com/login.aspx?culture=en-GB&BIGredirect=AABIG')

        login_form = self.browser.get_form('form2')
        login_form['ctl00$body$txtUsername'].value = credentials['email']
        login_form['ctl00$body$txtPassword'].value = credentials['password']
        self.browser.submit_form(login_form, submit=login_form.submit_fields['ctl00$body$btnLogin'])

        # Submit auth form.
        auth_form = self.browser.get_form()
        if auth_form and auth_form.action == 'https://loyalty.airasiabig.com/web/sso':
            self.browser.submit_form(auth_form)

        self.check_error('/login.aspx',
                         (('#body_divErrorMsg > span', STATUS_LOGIN_FAILED, 'Sorry, you have entered'), ))

    def balance(self):
        points = self.browser.select('span#body_lblBIGPointsBalance')[0].text
        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError('Implement when scraping transactions.')

    def scrape_transactions(self):
        return []
