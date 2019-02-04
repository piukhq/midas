import json
from decimal import Decimal

import arrow
import time
from gaia.user_token import UserTokenStore

from app.agents.base import MerchantApi
from settings import REDIS_URL


class Cooperative(MerchantApi):
    API_KEY = 'awmHjJzzfV3YMUuJdcmd56PKRIzg6KAg1WKn94Ds'
    AUTH_TOKEN_TIMEOUT = 3600
    new_request = None

    identifier_type = ['cardNumber', 'memberId']

    token_store = UserTokenStore(REDIS_URL)

    def balance(self):
        return {
            'points': Decimal(0),
            'value': 0,
            'value_label': '{} {}'.format(0, ''),
            'reward_tier': 0,
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transactions(row):
        return {
            'date': arrow.get(row['timestamp']),
            'description': row['reference'],
            'points': Decimal(row['balance_value']),
        }

    def get_merchant_ids(self, credentials):
        return {}

    def apply_security_measures(self, json_data, security_service, security_credentials, refresh_token=True):
        auth_token_header = "Authorization"
        try:
            if refresh_token:
                raise self.token_store.NoSuchToken

            access_token = json.loads(self.token_store.get(self.scheme_id))

            if self._token_is_valid(access_token['timestamp']):
                self.request = {
                    "json": json.loads(json_data),
                    "headers": {
                        auth_token_header: "{} {}".format(
                            security_credentials['outbound']['credentials'][0]['value']['prefix'],
                            access_token['token'])
                    }
                }
            else:
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            super().apply_security_measures(json_data, security_service, security_credentials)
            timestamp = time.time()

            self.request['headers'][auth_token_header] = self.request['headers']['Authorization']
            self.token_store.set(
                self.scheme_id,
                json.dumps({'token': self.request['headers'][auth_token_header], 'timestamp': timestamp})
            )

        self.request['headers']['X-API-KEY'] = Cooperative.API_KEY

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) > Cooperative.AUTH_TOKEN_TIMEOUT
