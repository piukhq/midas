import json
from decimal import Decimal

import arrow
import time
from gaia.user_token import UserTokenStore

from app.agents.base import MerchantApi
from app.configuration import Configuration
from settings import REDIS_URL


class Cooperative(MerchantApi):
    API_KEY = 'awmHjJzzfV3YMUuJdcmd56PKRIzg6KAg1WKn94Ds'
    AUTH_TOKEN_TIMEOUT = 3600
    AUTH_TOKEN_HEADER = "Authorization"

    new_request = None
    identifier_type = ['cardNumber', 'memberId']
    token_store = UserTokenStore(REDIS_URL)

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None, consents_data=None):
        super().__init__(retry_count, user_info, scheme_slug, config, consents_data)

        self.scope = None

        # Coop API requires a different scope parameter for each oauth call
        self.journey_to_scope = {
            Configuration.UPDATE_HANDLER: 'membership-api/get-balance',
            Configuration.VALIDATE_HANDLER: 'membership-api/verify-member',
            Configuration.JOIN_HANDLER: ['membership-api/register-members', 'membership-api/check-card']
        }

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

    def apply_security_measures(self, json_data, security_service, security_credentials, refresh_token=False):
        self.scope = self._get_scope()
        try:
            if refresh_token:
                raise self.token_store.NoSuchToken

            access_token = self._get_auth_token()

            if self._token_is_valid(access_token['timestamp']):
                self.request = {
                    "json": json.loads(json_data),
                    "headers": {
                        self.AUTH_TOKEN_HEADER: "{} {}".format(
                            security_credentials['outbound']['credentials'][0]['value']['prefix'],
                            access_token['token'])
                    }
                }
            else:
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            self._refresh_auth_token(json_data, security_service, security_credentials)

        self.request['headers']['X-API-KEY'] = Cooperative.API_KEY

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) < Cooperative.AUTH_TOKEN_TIMEOUT

    def _get_auth_token(self):
        return json.loads(self.token_store.get(f'{self.scheme_id}:{self.scope}'))

    def _refresh_auth_token(self, json_data, security_service, security_credentials):
        security_credentials['outbound']['credentials'][0]['value']['payload']['scope'] = self.scope
        super().apply_security_measures(json_data, security_service, security_credentials)

        timestamp = time.time()

        self.request['headers'][self.AUTH_TOKEN_HEADER] = self.request['headers']['Authorization']

        key = f"{self.scheme_id}:{self.scope}"
        token_data = json.dumps({'token': self.request['headers'][self.AUTH_TOKEN_HEADER], 'timestamp': timestamp})
        self.token_store.set(key, token_data)

    def _get_scope(self):
        handler_type = self.config.handler_type[0]

        if handler_type != Configuration.JOIN_HANDLER:
            scope = self.journey_to_scope[handler_type]
        else:
            # Must call verify if it is a ghost card
            if self.user_info['credentials'].get('card_number'):
                scope = self.journey_to_scope[handler_type][1]
            else:
                scope = self.journey_to_scope[handler_type][0]

        return scope
