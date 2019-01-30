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

    identifier_type = ['card_number', 'merchant_scheme_id2']

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

    def apply_security_measures(self, json_data, security_service, security_credentials):
        auth_token_header = "Access Token"
        try:
            access_token = json.loads(self.token_store.get(self.scheme_id))

            if self._token_is_valid(access_token['timestamp']):
                request = {
                    "json": json.loads(json_data),
                    "headers": {
                        auth_token_header: "{} {}".format(security_credentials['prefix'], access_token['token'])
                    }
                }
            else:
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            request = super().apply_security_measures(json_data, security_service, security_credentials)
            timestamp = time.time()

            request['headers'][auth_token_header] = request['headers'].pop('Authorization')
            self.token_store.set(
                self.scheme_id,
                json.dumps({'token': request['headers'][auth_token_header], 'timestamp': timestamp})
            )

        request['headers']['X-API-KEY'] = Cooperative.API_KEY

        return request

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) > Cooperative.AUTH_TOKEN_TIMEOUT
