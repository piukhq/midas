from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class AirAsia(Miner):
    def login(self, credentials):
        self.open_url('https://member.airasia.com/login.aspx?culture=en-GB&BIGredirect=AABIG')

        login_form = self.browser.get_form('form1')
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
        points = extract_decimal(self.browser.select('span.pts')[0].text)
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        # rows = self.browser.select('div.managepoints.box > table > tr')[1:]
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
