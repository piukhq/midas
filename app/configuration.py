import hvac
import requests

from app.agents.exceptions import AgentError, CONFIGURATION_ERROR
from settings import HELIOS_URL, SERVICE_API_KEY, VAULT_TOKEN, VAULT_URL


class Configuration:
    """
    Configuration for merchant API integration. Requires merchant id and handler type to retrieve
    configurations.
    Config parameters:
    - scheme_slug: merchant slug.
    - handler_type: join, update.
    - merchant_url: url of merchant endpoint.
    - callback_url: Endpoint url for merchant to call for response (Async processes only)
    - integration_service: sync or async process.
    - security_service: type of security to use e.g RSA.
    - security_credentials: credentials required for dealing with security e.g public/private keys.
    - retry_limit: number of times to retry on failed request.
    - log_level: level of logging to record e.g DEBUG for all, WARNING for warning logs and above.
    """
    UPDATE_HANDLER = 0
    JOIN_HANDLER = 1
    VALIDATE_HANDLER = 2

    HANDLER_TYPE_CHOICES = (
        (UPDATE_HANDLER, "Update"),
        (JOIN_HANDLER, "Join"),
        (VALIDATE_HANDLER, "Validate"),
    )

    SYNC_INTEGRATION = 0
    ASYNC_INTEGRATION = 1

    INTEGRATION_CHOICES = (
        (SYNC_INTEGRATION, "Sync"),
        (ASYNC_INTEGRATION, "Async"),
    )

    RSA_SECURITY = 0
    OPEN_AUTH_SECURITY = 1

    SECURITY_TYPE_CHOICES = (
        (RSA_SECURITY, "RSA"),
        (OPEN_AUTH_SECURITY, "Open Auth (No Authentication)")
    )

    DEBUG_LOG_LEVEL = 0
    INFO_LOG_LEVEL = 1
    WARNING_LOG_LEVEL = 2
    ERROR_LOG_LEVEL = 3
    CRITICAL_LOG_LEVEL = 4

    LOG_LEVEL_CHOICES = (
        (DEBUG_LOG_LEVEL, "Debug"),
        (INFO_LOG_LEVEL, "Info"),
        (WARNING_LOG_LEVEL, "Warning"),
        (ERROR_LOG_LEVEL, "Error"),
        (CRITICAL_LOG_LEVEL, "Critical")
    )

    def __init__(self, scheme_slug, handler_type):
        """
        :param scheme_slug: merchant identifier.
        :param handler_type: Int. A choice from Configuration.HANDLER_TYPE_CHOICES.
        """
        self.scheme_slug = scheme_slug
        self.handler_type = (handler_type, self.HANDLER_TYPE_CHOICES[handler_type][1].upper())

        self.data = self._get_config_data()
        self._process_config_data()

    def _get_config_data(self):
        params = {
            'merchant_id': self.scheme_slug,
            'handler_type': self.handler_type[0]
        }
        headers = {"Authorization": 'Token ' + SERVICE_API_KEY}

        try:
            resp = requests.get(HELIOS_URL + '/configuration', params=params, headers=headers)
        except requests.RequestException as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        if resp.status_code != 200:
            raise AgentError(CONFIGURATION_ERROR)

        return resp.json()

    def _process_config_data(self):
        self.merchant_url = self.data['merchant_url']
        self.integration_service = self.INTEGRATION_CHOICES[self.data['integration_service']][1].upper()
        self.security_service = self.SECURITY_TYPE_CHOICES[self.data['security_service']]
        self.retry_limit = self.data['retry_limit']
        self.log_level = self.LOG_LEVEL_CHOICES[self.data['log_level']][1].upper()
        self.callback_url = self.data['callback_url']
        self.country = self.data['country']

        try:
            self.security_credentials = self.get_security_credentials(self.data['security_credentials'])
        except TypeError as e:
            raise AgentError(CONFIGURATION_ERROR) from e

    @staticmethod
    def get_security_credentials(key_items):
        """
        Retrieves security credential values from key storage vault.
        :param key_items: list of dicts {'type': e.g 'bink_public_key', 'storage_key': auto-generated hash from helios}
        :return: key_items: returns same list of dict with added 'value' keys containing actual credential values.
        """
        client = hvac.Client(token=VAULT_TOKEN, url=VAULT_URL)

        try:
            for key_item in key_items:
                value = client.read('secret/data/{}'.format(key_item['storage_key']))['data']['data'][key_item['type']]
                key_item['value'] = value
        except TypeError as e:
            raise TypeError('Could not locate security credentials in vault.') from e

        return key_items
