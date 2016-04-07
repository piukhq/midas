from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow
import urllib


class AirAsia(Miner):
    def login(self, credentials):
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

    @staticmethod
    def parse_sso_cookie(sso_cookie):
        kv_strings = sso_cookie.split('&')
        sso_info = {}
        for kv_string in kv_strings:
            kv = kv_string.split('=')
            sso_info[kv[0]] = kv[1]
        return sso_info

    def balance(self):
        sso_info = self.parse_sso_cookie(self.browser.session.cookies.get('ssoSessionCookie').strip('"'))
        url = 'https://apim.airasiabig.com:8243/InternalTbdApi/1.0/getBalanceInternal?UserName={}&TicketId={}'.format(
            urllib.parse.quote(sso_info['UserName']),
            urllib.parse.quote(sso_info['TicketID'])
        )

        self.headers['Authorization'] = 'Bearer {}'.format(sso_info['Token'])
        self.open_url(url)

        loyalty_data = self.browser.response.json()
        return {
            'points': Decimal(loyalty_data['content']['AvailablePts']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # rows = self.browser.select('div.managepoints.box > table > tr')[1:]
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
