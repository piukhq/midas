import json
import logging
from copy import deepcopy
from typing import MutableMapping

import settings

LOG_FORMAT = "%(asctime)s | %(levelname)8s | %(name)s\n%(message)s"  # only used if JSON logging is disabled.

LOGGING_SENSITIVE_KEYS = [
    "address_1",
    "address_2",
    "country",
    "county",
    "dob",
    "email",
    "town_city",
    "phone1",
    "birthdate",
    "phone",
    "mobilphone",
] + settings.AUDIT_DEFAULT_SENSITIVE_KEYS


class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "timestamp": record.created,
                "level": record.levelno,
                "levelname": record.levelname,
                "process": record.processName,
                "thread": record.threadName,
                "file": record.pathname,
                "line": record.lineno,
                "module": record.module,
                "function": record.funcName,
                "name": record.name,
                "message": record.msg,
            }
        )


def sanitise(data: MutableMapping, sensitive_keys: list):
    data = deepcopy(data)
    for k, v in data.items():
        # if `k` is a sensitive key, redact the whole thing (even if it's a mapping itself.)
        if k.lower() in sensitive_keys:
            data[k] = settings.SANITISATION_STANDIN
        # if `k` isn't sensitive but it is a mapping, sanitise that mapping.
        elif isinstance(v, MutableMapping):
            data[k] = sanitise(v, sensitive_keys)
        # if `k` isn't sensitive but it is a list, sanitise all mappings in that list.
        elif isinstance(v, list):
            data[k] = [sanitise(item, sensitive_keys) for item in v if isinstance(item, MutableMapping)]
    return data


def get_logger(name: str) -> logging.Logger:
    """
    Returns a correctly configured logger with the given name.
    """
    logger = logging.getLogger(name.lower().replace(" ", "-"))

    # if this logger is already configured, return it now
    if logger.handlers:
        return logger

    logger.propagate = False

    formatter: logging.Formatter
    if settings.LOG_JSON:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT)

    handler = logging.StreamHandler()
    handler.setLevel(settings.LOG_LEVEL)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(settings.LOG_LEVEL)

    return logger
