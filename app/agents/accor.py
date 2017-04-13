from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow
import json


class Accor(Miner):
    point_conversion_rate = Decimal('0.0005')
    account_data = {}
    sid = ""

    def login(self, credentials):
        self.open_url('https://secure.accorhotels.com/authentication/login.jsp?appContext=&lang=gb&forceLogin=true'
                      '&gotoUrl=%2Fuser%2Fdashboard.action', verify=False)

        login_form = self.browser.get_form('login-form')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form, verify=False)

        self.sid = self.browser.session.cookies._cookies['.accorhotels.com']['/']['JSESSIONID'].value

        url = 'https://secure.accorhotels.com/bean/getViewBeans.action'
        params = {
            'beans': 'LoyaltyAccountViewBean',
            'httpSessionId': self.sid,
        }
        self.open_url(url, params=params, verify=False)

        response_text = self.browser.response.text[5:]
        self.account_data = json.loads(response_text)

        if not self.account_data['viewBeans']['LoyaltyAccountViewBean']['authenticated']:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points = self.account_data['viewBeans']['LoyaltyAccountViewBean']['account']['loyaltyCards'][0]['points']
        reward = self.calculate_tiered_reward(points, [
            (2000, '€40 discount on your next stay'),
        ])

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': reward,
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):

        return {
            'date': arrow.get(row.get('transactionDate')),
            'description': row.get('description'),
            'points': Decimal(row.get('rewardPoints')),
        }

    def scrape_transactions(self):
        transaction_url = 'https://secure.accorhotels.com/ajax/loyalty/transactions.action'
        parameters = {'httpSessionId': self.sid}
        self.open_url(transaction_url, params=parameters, verify=False)
        transaction_response = self.browser.response.text[5:]
        transactions_data = json.loads(transaction_response)
        transactions = transactions_data['viewBeans']['LoyaltyTransactionsViewBean']['loyaltyWrapper']['historyLines']

        return transactions
