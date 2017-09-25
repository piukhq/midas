from decimal import Decimal
import json

import arrow

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, AgentError, IP_BLOCKED, END_SITE_DOWN


class Qantas(RoboBrowserMiner):
    def login(self, credentials):
        self.card_number = credentials['card_number']
        data = {
            'memberId': self.card_number,
            'pin': credentials['pin'],
            'lastName': credentials['last_name'],
            'rememberMyDetails': False,
            'deviceFP': '3782cf03b50b41997dbe2ea466ac0b94'
        }

        url = 'https://api.services.qantasloyalty.com/auth/member/login'

        self.headers['content-type'] = 'application/json'
        self.headers['Accept'] = 'application/json'

        self.open_url(url, method="post", data=json.dumps(data))
        self.browser.response.raise_for_status()
        self.login_response_json = self.browser.response.json()

    # Override base class method
    def _raise_agent_exception(self, exc):
        member_info = json.loads(self.browser.response.content)
        if exc.response.status_code == 400 and member_info['auth']['status'] == 'INVALID_CREDENTIALS':
            raise LoginError(STATUS_LOGIN_FAILED)

        if exc.response.status_code == 403:
            raise AgentError(IP_BLOCKED) from exc

        raise AgentError(END_SITE_DOWN) from exc

    def balance(self):
        balance_response = self.browser.response.json()
        points = Decimal(balance_response['member']['points'])
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'YYYY-MM-DD'),
            'description': row['description'],
            'points': Decimal(row['qantasPoints']),
        }

    def scrape_transactions(self):
        transaction_url = 'https://api.services.qantasloyalty.com/api/member/{}/activity'.format(self.card_number)
        auth_token = self.login_response_json['auth']['token']['id']
        self.headers['Authorization'] = 'Bearer {}'.format(auth_token)
        params = {
            'start': '0',
            'size': '20',
        }
        self.open_url(transaction_url, params=params)

        transaction_response = self.browser.response.json()
        return transaction_response['transactions']
