from typing import Optional, Any

from app.agents.base import BaseAgent
from app.agents.schemas import Balance, Transaction
from app.reporting import get_logger

RETRY_LIMIT = 3
log = get_logger("template_slug")


class TemplateClassName(BaseAgent):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.source_id = "template_identifier"
        self.base_url = self.config.merchant_url
        self.integration_service = "SYNC"
        self.oauth_token_timeout = 3599
        self.outbound_security_credentials = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self.outbound_auth_service = self.config.security_credentials["outbound"]["service"]
        self.credentials = self.user_info["credentials"]
        self.errors = {}

    def join(self) -> Any:
        pass

    def login(self) -> Any:
        pass

    def transactions(self) -> list[Transaction]:
        pass

    def transaction_history(self) -> list[Transaction]:
        pass

    def parse_transaction(self, transaction: dict) -> Transaction:
        pass

    def balance(self) -> Optional[Balance]:
        pass
