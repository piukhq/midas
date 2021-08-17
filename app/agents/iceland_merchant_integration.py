from soteria.configuration import Configuration

from app.agents.merchant_api_generic import MerchantAPIGeneric


class Iceland(MerchantAPIGeneric):
    def __init__(self, retry_count, user_info, scheme_slug=None, config=None, consents_data=None):
        super().__init__(retry_count, user_info, scheme_slug, config, consents_data)
        self.audit_logger.journeys = (Configuration.JOIN_HANDLER, Configuration.VALIDATE_HANDLER)
