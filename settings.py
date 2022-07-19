import logging
import os
import typing as t

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from app.exceptions import (
    AccountAlreadyExistsError,
    CardNotRegisteredError,
    CardNumberError,
    JoinInProgressError,
    LinkLimitExceededError,
    NoSuchRecordError,
    PreRegisteredCardError,
    StatusLoginFailedError,
)
from app.version import __version__

os.chdir(os.path.dirname(__file__))


class ConfigVarRequiredError(Exception):
    pass


def getenv(key: str, default: str = None, conv: t.Callable = str, required: bool = True) -> t.Any:
    """If `default` is None, then the var is non-optional."""
    var = os.getenv(key, default)
    if var is None and required is True:
        raise ConfigVarRequiredError(f"Configuration variable '{key}' is required but was not provided.")
    elif var is not None:
        return conv(var)
    else:
        return None


def boolconv(s: str) -> bool:
    return s.lower() in ["true", "t", "yes"]


def listconv(s: str) -> list[str]:
    return s.split(",")


DEV_HOST = getenv("DEV_HOST", default="0.0.0.0")
DEV_PORT = getenv("DEV_PORT", default="8000", conv=int)

# Global logging level.
# Applies to any logger obtained through `app.reporting.get_logger`.
# https://docs.python.org/3/library/logging.html#logging-levels
LOG_LEVEL = getattr(logging, getenv("LOG_LEVEL", default="debug").upper())

# If enabled, logs will be emitted as JSON objects.
LOG_JSON = getenv("LOG_JSON", default="true", conv=boolconv)

JUNIT_XML_FILENAME = "test_results.xml"

SECRET_KEY = "QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR"

APP_DIR = os.path.abspath(os.path.dirname(__file__))
DEBUG = getenv("MIDAS_DEBUG", default="false", conv=boolconv)
LOCAL = getenv("MIDAS_LOCAL", default="false", conv=boolconv)

REDIS_PASSWORD = getenv("REDIS_PASSWORD", default="")
REDIS_HOST = getenv("REDIS_HOST", default="localhost")
REDIS_PORT = getenv("REDIS_PORT", default="6379")
REDIS_DB = getenv("REDIS_DB", default="0")
REDIS_URL = getenv("REDIS_URL", default=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

task_default_queue = "midas_consents"

AMQP_DSN = getenv("AMQP_DSN", "amqp://localhost:5672")

RETRY_PERIOD = getenv("RETRY_PERIOD", default="1800", conv=int)
broker_url = AMQP_DSN
worker_enable_remote_control = False  # Disables pidbox exchanges
task_serializer = "json"
beat_schedule = {"retry_tasks": {"task": "app.tasks.resend.retry_tasks", "schedule": RETRY_PERIOD, "args": ()}}
imports = ["app.tasks.resend"]
HADES_URL = getenv("HADES_URL", default="http://local.hades.chingrewards.com:8000")
HERMES_URL = getenv("HERMES_URL", default="http://local.hermes.chingrewards.com:8000")
CONFIG_SERVICE_URL = getenv("CONFIG_SERVICE_URL", default="")
ATLAS_URL = getenv("ATLAS_URL", default="http://localhost:8100")

SERVICE_API_KEY = "F616CE5C88744DD52DB628FAD8B3D"

SENTRY_DSN = getenv("SENTRY_DSN", required=False)
SENTRY_ENV = getenv("SENTRY_ENV", required=False)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[FlaskIntegration(), RedisIntegration()],
        release=__version__,
        ignore_errors=[
            AccountAlreadyExistsError,
            CardNotRegisteredError,
            CardNumberError,
            JoinInProgressError,
            LinkLimitExceededError,
            NoSuchRecordError,
            PreRegisteredCardError,
            StatusLoginFailedError,
        ],
    )

if getenv("POSTGRES_DSN", required=False):
    POSTGRES_DSN = getenv("POSTGRES_DSN").format(getenv("POSTGRES_DB", "midas"))
else:
    POSTGRES_HOST = getenv("POSTGRES_HOST")
    POSTGRES_PORT = getenv("POSTGRES_PORT", default="5432", conv=int)
    POSTGRES_USER = getenv("POSTGRES_USER")
    POSTGRES_PASS = getenv("POSTGRES_PASS", required=False)
    POSTGRES_DB = getenv("POSTGRES_DB")

    POSTGRES_DSN = "".join(
        [
            "postgresql+psycopg2://",
            POSTGRES_USER,
            f":{POSTGRES_PASS}" if POSTGRES_PASS else "",
            "@",
            POSTGRES_HOST,
            ":",
            str(POSTGRES_PORT),
            "/",
            POSTGRES_DB,
        ]
    )

QUERY_TRACE_LEVEL = getenv("QUERY_TRACE_LEVEL", default="0", conv=int)

# These are set automatically based on the above.
TRACE_QUERY_DESCRIPTIONS = QUERY_TRACE_LEVEL > 0
TRACE_QUERY_SQL = QUERY_TRACE_LEVEL > 1

PROPAGATE_EXCEPTIONS = True

MAX_VALUE_LABEL_LENGTH = 11

VAULT_URL = getenv("VAULT_URL", default="http://localhost:8200")
# Vault settings for merchant api security credential storage
VAULT_TOKEN = getenv("VAULT_TOKEN", default="myroot")


BACK_OFF_COOLDOWN = 120

HERMES_CONFIRMATION_TRIES = 10

ENABLE_ICELAND_VALIDATE = getenv("ENABLE_ICELAND_VALIDATE", default="false", conv=boolconv)


# Prometheus settings
PUSH_PROMETHEUS_METRICS = getenv("PUSH_PROMETHEUS_METRICS", default="true", conv=boolconv)
PROMETHEUS_PUSH_GATEWAY = "http://localhost:9100"
PROMETHEUS_JOB = "midas"

API_AUTH_ENABLED = getenv("TXM_API_AUTH_ENABLED", default="true", conv=boolconv)


# olympus-messaging interface
LOYALTY_REQUEST_QUEUE = getenv("LOYALTY_REQUEST_QUEUE", default="loyalty-request")
LOYALTY_RESPONSE_QUEUE = getenv("LOYALTY_RESPONSE_QUEUE", default="loyalty-response")

# Whether to include Midas' default sensitive keys in the audit sanitisation process.
AUDIT_USE_DEFAULT_SENSITIVE_KEYS = getenv("AUDIT_USE_DEFAULT_SENSITIVE_KEYS", default="true", conv=boolconv)

# Additional keys to include in the audit sanitisation process.
AUDIT_ADDITIONAL_SENSITIVE_KEYS = getenv("AUDIT_ADDITIONAL_SENSITIVE_KEYS", required=False, conv=listconv)

# String to replace sanitised keys in audit logs with.
SANITISATION_STANDIN = getenv("AUDIT_SANITISATION_STANDIN", default="********")

# Combined set of keys to redact from audit logs.
AUDIT_DEFAULT_SENSITIVE_KEYS = ["password", "passwd", "pwd", "pw", "key", "secret", "token"]

AUDIT_SENSITIVE_KEYS = []
if AUDIT_USE_DEFAULT_SENSITIVE_KEYS:
    AUDIT_SENSITIVE_KEYS += AUDIT_DEFAULT_SENSITIVE_KEYS

if AUDIT_ADDITIONAL_SENSITIVE_KEYS:
    AUDIT_SENSITIVE_KEYS += AUDIT_ADDITIONAL_SENSITIVE_KEYS

MAX_RETRY_COUNT = getenv("MAX_RETRY_COUNT", default="3", conv=int)
MAX_CALLBACK_RETRY_COUNT = getenv("MAX_CALLBACK_RETRY_COUNT", default="3", conv=int)
RETRY_BACKOFF_BASE = getenv("RETRY_BACKOFF_BASE", default="3", conv=int)
DEFAULT_FAILURE_TTL = getenv("DEFAULT_FAILURE_TTL", default=str((60 * 60 * 24 * 7)), conv=int)
