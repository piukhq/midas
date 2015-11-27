from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class FlyingBlue(Miner):
    def login(self, credentials):
        url = 'https://www.flyingblue.com/account/login/process.html'
        data = {
            'uid': credentials['card_number'],
            'pwd': credentials['pin'],
        }
        self.open_url(url, method='post', data=data)

        response = self.browser.response.json()
        if response['status'] == 'false':
            problem = response['errors'][0]['fieldname']

            if problem == 'uid' or problem == 'pwd':
                raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.open_url('https://www.flyingblue.com/index.html')
        points = extract_decimal(self.browser.select('div.fb-memberinfo-milesbalance')[0].text)
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
        # overview_link = self.browser.select('#overlay_account > div > div.menuRight > div > ul > li > a')[0].href
        # self.open_url(overview_link)
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
