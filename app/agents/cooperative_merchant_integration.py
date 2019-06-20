import json
import time
from decimal import Decimal

import arrow
import requests
from gaia.user_token import UserTokenStore

from app.agents.base import MerchantApi
from app.agents.exceptions import LoginError, NOT_SENT, errors, UNKNOWN, STATUS_LOGIN_FAILED, PRE_REGISTERED_CARD, \
    CARD_NUMBER_ERROR, VALIDATION, JOIN_ERROR, UnauthorisedError, ACCOUNT_ALREADY_EXISTS, CARD_NOT_REGISTERED, \
    SCHEME_REQUESTED_DELETE, AgentError, CONFIGURATION_ERROR
from app.configuration import Configuration
from app.security.utils import get_security_agent
from app.utils import create_error_response, JourneyTypes, TWO_PLACES
from settings import REDIS_URL, logger


class Cooperative(MerchantApi):
    AUTH_TOKEN_TIMEOUT = 3600
    AUTH_TOKEN_HEADER = "Authorization"

    new_request = None
    identifier_type = ['cardNumber', 'memberId']
    merchant_identifier_mapping = {
        'cardNumber': 'card_number',
        'memberId': 'merchant_identifier',
    }

    token_store = UserTokenStore(REDIS_URL)

    def __init__(self, retry_count, user_info, scheme_slug=None, config=None, consents_data=None):
        super().__init__(retry_count, user_info, scheme_slug, config, consents_data)

        journey_to_handler = {
            JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
            JourneyTypes.LINK: Configuration.VALIDATE_HANDLER
        }
        try:
            self.config = Configuration(scheme_slug, journey_to_handler[self.user_info['journey_type']])
        except KeyError:
            self.config = Configuration(scheme_slug, Configuration.UPDATE_HANDLER)

        # To change the request contents, using a function, based on the type of journey.
        self.handler_type_to_updated_request = {
            Configuration.JOIN_HANDLER: self._update_join_request,
            Configuration.VALIDATE_HANDLER: self._update_validate_request,
            Configuration.UPDATE_HANDLER: self._update_balance_request
        }
        # For journey specific error handling.
        self.handler_type_to_error_handler = {
            Configuration.JOIN_HANDLER: self._join_error_handler,
            Configuration.VALIDATE_HANDLER: self._validate_error_handler,
            Configuration.UPDATE_HANDLER: self._update_error_handler
        }
        # Coop API requires a different scope parameter for each oauth call
        self.journey_to_scope = {
            Configuration.UPDATE_HANDLER: 'membership-api/get-balance',
            Configuration.VALIDATE_HANDLER: 'membership-api/verify-member',
            Configuration.JOIN_HANDLER: 'membership-api/register-members',
            'check_card': 'membership-api/check-card'
        }
        # { error we raise: error we receive in merchant payload }
        self.errors = {
            NOT_SENT: ['NOT_SENT'],
            VALIDATION: ['VALIDATION'],
            PRE_REGISTERED_CARD: ['PRE_REGISTERED_CARD'],
            UNKNOWN: ['UNKNOWN'],
            CARD_NUMBER_ERROR: ['CARD_NUMBER_ERROR'],
            JOIN_ERROR: ['JOIN_ERROR'],
            STATUS_LOGIN_FAILED: ['STATUS_LOGIN_FAILED'],
            SCHEME_REQUESTED_DELETE: ['SCHEME_REQUESTED_DELETE'],
        }

        self.scope = self._get_scope()

    def balance(self):
        balance = self.result['balance'] / 100
        value = Decimal(balance).quantize(TWO_PLACES)
        return {
            "points": value,
            "value": value,
            "value_label": '£{}'.format(value),
        }

    def scrape_transactions(self):
        return self.result['transactions']

    @staticmethod
    def parse_transactions(row):
        charity_value = Decimal(row['balance']['value']) / 100
        transaction_value = Decimal(row['balance']['value']) / 100

        return {
            'date': arrow.get(row['timestamp']),
            'description': 'Charity: £{}'.format(charity_value.quantize(TWO_PLACES)),
            'points': transaction_value.quantize(TWO_PLACES),
        }

    def get_merchant_ids(self, credentials):
        return {}

    def apply_security_measures(self, json_data, security_service, security_credentials):
        try:
            access_token = self._get_auth_token(self.scope)
            if not self._token_is_valid(access_token['timestamp']):
                raise self.token_store.NoSuchToken

        except self.token_store.NoSuchToken:
            access_token = self._refresh_auth_token(json_data, security_service, security_credentials, self.scope)

        self.request = {
            "json": json.loads(json_data),
            "headers": {
                self.AUTH_TOKEN_HEADER: "{} {}".format(
                    security_credentials['outbound']['credentials'][0]['value']['prefix'],
                    access_token['token']),
                'X-API-KEY': self._get_api_key()
            }
        }

    @staticmethod
    def _token_is_valid(timestamp):
        current_time = time.time()
        return (current_time - timestamp) < Cooperative.AUTH_TOKEN_TIMEOUT

    def _get_auth_token(self, scope):
        return json.loads(self.token_store.get(f'{scope}'))

    def _refresh_auth_token(self, json_data, security_service, security_credentials, scope):
        security_credentials['outbound']['credentials'][0]['value']['payload']['scope'] = scope
        outbound_security_agent = get_security_agent(security_service, security_credentials)

        request = outbound_security_agent.encode(json_data)

        timestamp = time.time()
        key = f"{scope}"
        token_data = {
            'token': request['headers'][self.AUTH_TOKEN_HEADER].split()[1],
            'timestamp': timestamp
        }
        self.token_store.set(key, json.dumps(token_data))

        return token_data

    def _get_scope(self):
        handler_type = self.config.handler_type[0]
        return self.journey_to_scope[handler_type]

    def _send_request(self):
        handler_type = self.config.handler_type[0]
        response_json, status = self.handler_type_to_updated_request[handler_type]()

        return response_json, status

    def _card_is_temporary(self, card_number):
        scope_key = 'check_card'
        headers = self._get_auth_headers(scope_key)

        check_card_config = Configuration(self.scheme_slug, Configuration.CHECK_MEMBERSHIP_HANDLER)

        full_url = check_card_config.merchant_url.format(card_number=card_number)
        resp = requests.get(full_url, headers=headers)

        if resp.status_code == 404:
            raise LoginError(CARD_NUMBER_ERROR)
        elif resp.status_code == 401:
            self.token_store.delete(self.journey_to_scope[scope_key])
            raise UnauthorisedError

        resp_json = resp.json()
        if resp_json:
            return resp_json['isTemporary']

    def _update_join_request(self):
        old_json = self.request['json']
        card_number = old_json.get('card_number')

        try:
            if card_number and not self._card_is_temporary(card_number):
                return (create_error_response(ACCOUNT_ALREADY_EXISTS, errors[ACCOUNT_ALREADY_EXISTS]['name']),
                        errors[ACCOUNT_ALREADY_EXISTS]['code'])
        except KeyError:
            return (create_error_response(UNKNOWN, errors[UNKNOWN]['name'] + ' isTemporary not in check card response'),
                    errors[UNKNOWN]['code'])
        except LoginError:
            return (create_error_response(STATUS_LOGIN_FAILED, errors[STATUS_LOGIN_FAILED]['name']),
                    errors[STATUS_LOGIN_FAILED]['code'])

        old_json = self.request['json']
        new_json = {
            'title': old_json['title'],
            'dateOfBirth': old_json['dob'],
            'firstName': old_json['first_name'],
            'lastName': old_json['last_name'],
            'email': old_json['email'],
            'address': {
                'addressLine1': old_json['address_1'],
                'city': old_json['town_city'],
                'postcode': old_json['postcode']
            }
        }

        if card_number:
            new_json['temporaryCardNumber'] = card_number

        self.new_request = self.request.copy()
        self.new_request['json'] = new_json

        response = requests.post(self.config.merchant_url, **self.new_request)
        handler_type = self.config.handler_type[0]

        validated_response = self.handler_type_to_error_handler[handler_type](response)
        validated_response_dict = json.loads(validated_response)
        if validated_response_dict.get('error_codes'):
            return validated_response, response.status_code

        self.user_info['credentials']['merchant_identifier'] = validated_response_dict['memberId']
        return validated_response, response.status_code

    def _error_handler(self, response):
        status = response.status_code

        logger.debug(f"raw_response: {response.text}, scheme_account: {self.scheme_id}")

        if status == 200:
            inbound_security_agent = get_security_agent(Configuration.OPEN_AUTH_SECURITY)
            response_json = inbound_security_agent.decode(response.headers, response.text)
            self.log_if_redirect(response, response_json)
        elif status == 401:
            self.token_store.delete(self.scope)
            raise UnauthorisedError
        elif status in [503, 504, 408]:
            error_suffix = ' merchant returned status {}'.format(status)
            response_json = create_error_response(NOT_SENT, errors[NOT_SENT]['name'] + error_suffix)
        else:
            error_suffix = ' with status code {}'.format(status)
            response_json = create_error_response(UNKNOWN, errors[UNKNOWN]['name'] + error_suffix)
        return response_json

    def _update_validate_request(self):
        card_number = self.request['json']['card_number']
        try:
            if self._card_is_temporary(card_number):
                return (create_error_response(PRE_REGISTERED_CARD, errors[PRE_REGISTERED_CARD]['name']),
                        errors[PRE_REGISTERED_CARD]['code'])
        except KeyError:
            return (create_error_response(UNKNOWN, errors[UNKNOWN]['name'] + ' isTemporary not in check card response'),
                    errors[UNKNOWN]['code'])

        old_json = self.request['json']
        new_json = {
            'cardNumber': old_json['card_number'],
            'dateOfBirth': old_json['dob'],
            'postcode': old_json['postcode']
        }

        self.new_request = self.request.copy()
        self.new_request['json'] = new_json

        response = requests.post(self.config.merchant_url, **self.new_request)

        handler_type = self.config.handler_type[0]
        validated_response = self.handler_type_to_error_handler[handler_type](response)
        validated_response_dict = json.loads(validated_response)
        if validated_response_dict.get('error_codes'):
            return validated_response, response.status_code

        member_id = validated_response_dict['memberId']
        response_json, balance_status = self._get_balance(member_id)

        response_dict = json.loads(response_json)
        response_dict['memberId'] = member_id

        return json.dumps(response_dict), balance_status

    def _update_balance_request(self):
        member_id = self.request['json']['merchant_identifier']
        return self._get_balance(member_id)

    def _join_error_handler(self, response):
        response_json = self._error_handler(response)
        if response.status_code in [400, 404]:
            return self.generate_response_from_error_codes(response)
        return response_json

    def _validate_error_handler(self, response):
        response_json = self._error_handler(response)

        if response.status_code in [400, 404]:
            return self.generate_response_from_error_codes(response)

        response_dict = json.loads(response_json)
        errors_in_resp = self._check_for_error_response(response_dict)
        if not errors_in_resp and not response_dict.get('isVerified'):
            return create_error_response(STATUS_LOGIN_FAILED, errors[STATUS_LOGIN_FAILED]['name'])
        return response_json

    def _update_error_handler(self, response):
        response_json = self._error_handler(response)

        try:
            response_dict = json.loads(response_json)
            error_resp = self._check_for_error_response(response_dict)
        except json.JSONDecodeError:
            return response_json

        if response.status_code == 400 and error_resp:
            if error_resp['code'] == 'CARD_NOT_FOUND':
                return (create_error_response(SCHEME_REQUESTED_DELETE, errors[SCHEME_REQUESTED_DELETE]['name']),
                        errors[SCHEME_REQUESTED_DELETE]['code'])

        return response_json

    def _get_balance(self, member_id):
        balance_handler = Configuration.UPDATE_HANDLER
        headers = self._get_auth_headers(balance_handler)

        if self.config and self.config.handler_type == Configuration.UPDATE_HANDLER:
            balance_config = self.config
        else:
            balance_config = Configuration(self.scheme_slug, balance_handler)

        full_url = balance_config.merchant_url.format(member_id=member_id)
        response = requests.get(full_url, headers=headers)
        return self.handler_type_to_error_handler[balance_handler](response), response.status_code

    def _get_auth_headers(self, scope_key):
        scope = self.journey_to_scope[scope_key]
        security_service = self.config.security_credentials['outbound']['service']
        security_credentials = self.config.security_credentials.copy()

        try:
            access_token = self._get_auth_token(scope)

            if not self._token_is_valid(access_token['timestamp']):
                access_token = self._refresh_auth_token('{}', security_service, security_credentials, scope)

        except self.token_store.NoSuchToken:
            access_token = self._refresh_auth_token('{}', security_service, security_credentials, scope)

        return {
            self.AUTH_TOKEN_HEADER: "{} {}".format(
                security_credentials['outbound']['credentials'][0]['value']['prefix'],
                access_token['token']
            ),
            'X-API-KEY': self._get_api_key()
        }

    def generate_response_from_error_codes(self, response):
        """
        Assumes the response is an error response.
        Parses the response json and converts the response error codes to internal error codes.
        :param response: Response object
        :return: JSON string of converted response
        """
        inbound_security_agent = get_security_agent(Configuration.OPEN_AUTH_SECURITY)
        response_json = inbound_security_agent.decode(response.headers, response.text)

        error_mapping = {
            VALIDATION: ['VALIDATION_FAILED'],
            STATUS_LOGIN_FAILED: ['VERIFICATION_FAILURE'],
            ACCOUNT_ALREADY_EXISTS: ['DUPLICATE_REGISTRATION'],
            PRE_REGISTERED_CARD: ['INVALID_TEMP_CARD'],
            CARD_NOT_REGISTERED: ['CARD_NOT_FOUND']
        }
        error = self._check_for_error_response(json.loads(response_json))
        if error:
            for key, values in error_mapping.items():
                if error[0]['code'] in values:
                    return create_error_response(key, errors[key]['name'])

        return create_error_response(UNKNOWN, errors[UNKNOWN]['name'])

    def _get_api_key(self):
        try:
            return self.config.security_credentials['outbound']['credentials'][0]['value']['api_key']
        except KeyError as e:
            raise AgentError(CONFIGURATION_ERROR) from e
