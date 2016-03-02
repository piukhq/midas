from app.agents.base import Miner
from app.agents.exceptions import LoginError, TRIPPED_CAPTCHA, UNKNOWN, IP_BLOCKED
from decimal import Decimal
import arrow


class ChoiceHotels(Miner):
    def login(self, credentials):
        url = 'https://www.choicehotels.com/webapi/user-account/login'
        data = {
            'username': credentials['username'],
            'password': credentials['password'],
            'include': 'year_to_date_nights%2Cppc_status',
            'preferredLanguageCode': 'EN',
        }

        self.browser.open(url, method='post', data=data)

        if self.browser.response.status_code != 200:
            if 'failed attempts from your IP' in self.browser.response.text:
                raise LoginError(IP_BLOCKED)
            else:
                resp = self.browser.response.json()
                if resp['status'] == 'ERROR':
                    if 'INVALID_LOYALTY_MEMBER_AUTHENTICATION_TOKEN' in resp['outputErrors']:
                        raise LoginError(TRIPPED_CAPTCHA)
                    else:
                        raise LoginError(UNKNOWN)

    def balance(self):
        data = self.browser.response.json()

        return {
            'points': Decimal(data['loyaltyAccounts'][0]['accountBalance']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://portal.prepaytec.com/chopinweb/scareMyStatement.do')
        # transaction_table = self.browser.select('table.txnHistory')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
