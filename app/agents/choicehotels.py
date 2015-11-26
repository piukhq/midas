from app.agents.base import Miner
from decimal import Decimal
import arrow


class ChoiceHotels(Miner):
    def login(self, credentials):
        url = 'https://www.choicehotels.com/webapi/user-account/login'
        data = {
            'include': 'year_to_date_nights%2Cppc_status',
            'password': credentials['password'],
            'preferredLanguageCode': 'EN',
            'username': credentials['username'],
        }

        self.open_url(url, method='post', data=data)

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

    def transactions(self):
        # self.open_url('https://portal.prepaytec.com/chopinweb/scareMyStatement.do')
        # transaction_table = self.browser.select('table.txnHistory')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
