from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.agents.base import ApiMiner
from app.reporting import get_logger

log = get_logger("iceland")


class Iceland(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.credentials = user_info["credentials"]
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        self.token_store = UserTokenStore(settings.REDIS_URL)
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
