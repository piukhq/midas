import json

import requests

from app.security import get_security_credentials


class Configuration:
    config_service_url = 'http://127.0.0.1:8002/dashboard/configuration'

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
        self.handler_type = handler_type

        self.data = self._get_config_data()
        self._process_config_data(self.data)
        print()

    def _get_config_data(self):

        # TODO: error handling
        params = {
            'merchant_id': self.merchant_id,
            'handler_type': self.handler_type
        }

        json_data = requests.get(self.config_service_url, params=params).content.decode('utf8')
        data = json.loads(json_data)

        return data

    def _process_config_data(self, data):
        self.merchant_url = data['merchant_url']
        self.integration_service = self.INTEGRATION_CHOICES[data['integration_service']][1].upper()
        self.security_service = self.SECURITY_TYPE_CHOICES[data['security_service']][1].upper()
        self.retry_limit = data['retry_limit']
        self.log_level = self.LOG_LEVEL_CHOICES[data['log_level']][1].upper()
        self.callback_url = data['callback_url']

        self.security_credentials = self._get_security_credentials()

    def _get_security_credentials(self):
        """
        For use by security services and handled according to security type.
        :return: List of dicts. Keys will depend on security service.
        """
        # data['security_credentials'] contain keys to retrieve actual credential values from vault.
        credentials = get_security_credentials(self.data['security_credentials'])

        return credentials
