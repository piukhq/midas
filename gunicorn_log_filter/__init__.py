import logging
import re

from gunicorn import glogging


class RedactingFilter(logging.Filter):

    def __init__(self, patterns):
        super(RedactingFilter, self).__init__()
        self._patterns = patterns

    def filter(self, record):
        record.msg = self.redact(record.msg)
        if isinstance(record.args, dict):
            for k in record.args.keys():
                record.args[k] = self.redact(record.args[k])
        else:
            record.args = tuple(self.redact(arg) for arg in record.args)
        return True

    def redact(self, msg):
        if isinstance(msg, str):
            for pattern in self._patterns:
                msg = re.sub(pattern, "credentials=[REDACTED]", msg)
        return msg


class Logger(glogging.Logger):
    """Custom logger for Gunicorn log messages."""

    def setup(self, cfg):
        super().setup(cfg)

        patterns = [re.compile(r"credentials=[a-zA-Z0-9+/=]*"), ]
        self.access_log.addFilter(RedactingFilter(patterns))
        self.error_log.addFilter(RedactingFilter(patterns))
