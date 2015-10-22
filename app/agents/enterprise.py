from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, UNKNOWN, AgentError
from app.utils import extract_decimal
from decimal import Decimal
from urllib.parse import urlsplit
import arrow
import re


class Enterprise(Miner):
    redemption_miles_pat = re.compile('"redemptionMiles":"(\d+)"')

    def login(self, credentials):
        self.open_url('https://www.enterprise.co.uk/car_rental/home.do')

        login_form = self.browser.get_form(action='/car_rental/enterprisePlusLoginWidget.do')
        login_form['memberNumber'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'p.errorText'

        # We can't just check_error because the page for a correct login is the same as that of an incorrect one.
        error_box = self.browser.select(selector)
        if error_box:
            self.check_error('/car_rental/enterprisePlusLoginWidget.do', ((selector, STATUS_LOGIN_FAILED, "We're sorry"),))

    def balance(self):
        parts = urlsplit(self.browser.url)

        if parts.path == '/car_rental/enterprisePlusLoginWidget.do':
            points = extract_decimal(self.browser.select('#loyaltyWidgetHomeContainer form p strong')[2].text)
        elif parts.path == '/group/ehi/account-activity':
            user_data_script = self.browser.select('script')[10].text
            matches = self.redemption_miles_pat.findall(user_data_script)
            points = extract_decimal(matches[0])
        else:
            # TODO: This should be an 'end site changed' error, or something like that.
            raise AgentError(UNKNOWN)

        return {
            'points': points
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        self.open_url('https://www.enterprise.co.uk/car_rental/enterprisePlusMyAccount.do?redirect=accountHistory&transactionId=WebTransaction2')

        redir_form = self.browser.get_form('enterprisePlusSSORedirectForm')
        self.browser.submit_form(redir_form)

        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
