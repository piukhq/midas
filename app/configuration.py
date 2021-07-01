import requests
import soteria.configuration

from app.agents.exceptions import AgentError, SERVICE_CONNECTION_ERROR, CONFIGURATION_ERROR
import settings

# Lower SSL cipher list to allow HN
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'    # type: ignore


class Configuration(soteria.configuration.Configuration):
    def __init__(self, scheme_slug, handler_type):
        super().__init__(
            scheme_slug,
            handler_type,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL
        )

    def _get_config_data(self, config_service_url):
        try:
            return super()._get_config_data(config_service_url)
        except soteria.configuration.ConfigurationException as ex:
            raise AgentError(SERVICE_CONNECTION_ERROR, message='Error connecting to configuration service.') from ex

    def get_security_credentials(self, key_items):
        try:
            return super().get_security_credentials(key_items)
        except soteria.configuration.ConfigurationException as ex:
            raise AgentError(CONFIGURATION_ERROR, message='Could not locate security credentials in vault.') from ex
