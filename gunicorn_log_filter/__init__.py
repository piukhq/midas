import logging
import re

from gunicorn import glogging

creds_query = re.compile(r"credentials=[a-zA-Z0-9+/=]*")


class CredentialFilter(logging.Filter):
    def filter(self, record):
        record.msg = creds_query.sub("credentials=[REDACTED]", record.msg)
        return True


class Logger(glogging.Logger):
    """Custom logger for Gunicorn log messages."""

    def setup(self, cfg):
        super().setup(cfg)

        logger = logging.getLogger("gunicorn")
        logger.addFilter(CredentialFilter())
