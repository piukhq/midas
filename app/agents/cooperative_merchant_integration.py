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
        value = Decimal(self.result['alt_value'])
        value_units = self.result['alt_unit']
        tier_list = {
            'Platinum': 0,
            'Black': 1
        }
        tier = tier_list[self.result['tier']]

        return {
            'points': Decimal(self.result['balance_value']),
            'value': value,
            'value_label': '{} {}'.format(value, value_units),
            'reward_tier': tier,
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
        merchant_ids = {
            'merchant_scheme_id1': credentials['email'],
            'merchant_scheme_id2': credentials.get('merchant_identifier')
        }

        return merchant_ids

    def apply_security_measures(self, json_data, security_service, security_credentials):
        auth_token_header = "Access Token"
        try:
            access_token = self.token_store.get(self.scheme_id)

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
                {'token': request['headers'][auth_token_header], 'timestamp': timestamp}
            )

        request['headers']['X-API-KEY'] = Cooperative.API_KEY

        return request

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) > Cooperative.AUTH_TOKEN_TIMEOUT
