import json

import requests

from app.security import get_security_credentials
from settings import HELIOS_URL


class Configuration:
    """
    Configuration for merchant API integration. Requires merchant id and handler type to retrieve
    configurations.
    Config parameters:
    - merchant_id: merchant slug.
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

    SECURITY_TYPE_CHOICES = (
        (RSA_SECURITY, "RSA"),
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

    def __init__(self, merchant_id, handler_type):

        self.merchant_id = merchant_id
        self.handler_type = self.HANDLER_TYPE_CHOICES[handler_type][1].upper()

        self.data = self._get_config_data()
        self._process_config_data()

    def _get_config_data(self):
        params = {
            'merchant_id': self.merchant_id,
            'handler_type': self.handler_type
        }

        json_data = requests.get(HELIOS_URL + '/configuration', params=params).content.decode('utf8')
        data = json.loads(json_data)

        return data

    def _process_config_data(self):
        self.merchant_url = self.data['merchant_url']
        self.integration_service = self.INTEGRATION_CHOICES[self.data['integration_service']][1].upper()
        self.security_service = self.SECURITY_TYPE_CHOICES[self.data['security_service']][1].upper()
        self.retry_limit = self.data['retry_limit']
        self.log_level = self.LOG_LEVEL_CHOICES[self.data['log_level']][1].upper()
        self.callback_url = self.data['callback_url']

        self.security_credentials = get_security_credentials(self.data['security_credentials'])
