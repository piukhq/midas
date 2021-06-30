import logging
import os
import typing as t

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from app.exceptions import SENTRY_IGNORED_EXCEPTIONS
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


DEV_HOST = getenv('DEV_HOST', '0.0.0.0')
DEV_PORT = getenv('DEV_PORT', '8000')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
logger = logging.getLogger('midas_logger')
logger.setLevel(logging.DEBUG)

SLACK_API_KEY = 'xoxp-10814716850-12751177555-33955253125-1750700274'
JUNIT_XML_FILENAME = 'test_results.xml'

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = getenv('MIDAS_DEBUG', default="false")
LOCAL = getenv('MIDAS_LOCAL', default="false")
AES_KEY = '6gZW4ARFINh4DR1uIzn12l7Mh1UF982L'

REDIS_PASSWORD = getenv('REDIS_PASSWORD', '')
REDIS_HOST = getenv('REDIS_HOST', 'localhost')
REDIS_PORT = getenv('REDIS_PORT', '6379')
REDIS_DB = getenv('REDIS_DB', '0')
REDIS_URL = getenv('REDIS_URL', f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')

RETRY_PERIOD = getenv('RETRY_PERIOD', '1800')
REDIS_CELERY_DB = getenv('REDIS_CELERY_DB', '1')
CELERY_BROKER_URL = getenv(
    'AMQP_DSN',
    f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}'
)
CELERY_TASK_SERIALIZER = 'json'
CELERYBEAT_SCHEDULE = {
    'retry_tasks': {
        'task': 'app.tasks.resend.retry_tasks',
        'schedule': int(RETRY_PERIOD),
        'args': ()
    }
}
CELERY_IMPORTS = [
    'app.tasks.resend'
]

HADES_URL = getenv('HADES_URL', 'http://local.hades.chingrewards.com:8000')
HERMES_URL = getenv('HERMES_URL', 'http://local.hermes.chingrewards.com:8000')
HELIOS_URL = getenv('HELIOS_URL', 'https://api.bink-dev.xyz/dashboard')
HEARTBEAT_URL = getenv('HEARTBEAT_URL', 'https://hchk.io/976b50d5-1616-4c7e-92ac-6e05e0916e82')
CONFIG_SERVICE_URL = getenv('CONFIG_SERVICE_URL', '')
ATLAS_URL = getenv('ATLAS_URL', 'http://localhost:8100')

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DSN = getenv('SENTRY_DSN', required=False)
SENTRY_ENV = getenv('SENTRY_ENV', required=False)
if SENTRY_DSN:
    def ignore_errors(event, hint):
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if isinstance(exc_value, SENTRY_IGNORED_EXCEPTIONS):
                return None
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[
            FlaskIntegration()
        ],
        release=__version__,
        before_send=ignore_errors,
    )

PROPAGATE_EXCEPTIONS = True

INFLUX_HOST = getenv('INFLUX_HOST', '192.168.1.53')
INFLUX_PORT = getenv('INFLUX_PORT', '8086')
INFLUX_USER = getenv('INFLUX_USER', 'root')
INFLUX_PASSWORD = getenv('INFLUX_PASSWORD', 'root')
INFLUX_DATABASE = getenv('INFLUX_DATABASE', 'test_results')

MAX_VALUE_LABEL_LENGTH = 11

HELIOS_DB_USER = getenv('HELIOS_DB_USER', 'helios')
HELIOS_DB_PASS = getenv('HELIOS_DB_PASS', 'j8NUz3vzPSn$')
HELIOS_DB_HOST = getenv('HELIOS_DB_HOST', '127.0.0.1')
HELIOS_DB_PORT = getenv('HELIOS_DB_PORT', '5432')
HELIOS_DB_NAME = getenv('HELIOS_DB_NAME', 'helios')

HELIOS_DB_URI = (
    'postgresql+psycopg2://'
    f'{HELIOS_DB_USER}:{HELIOS_DB_PASS}@{HELIOS_DB_HOST}:{HELIOS_DB_PORT}/{HELIOS_DB_NAME}'
)

CREDENTIALS_LOCAL = getenv('CREDENTIALS_LOCAL', default="false")
LOCAL_CREDENTIALS_FILE = os.path.join(APP_DIR, 'app', 'tests', 'service', 'credentials', 'credentials.json')

VAULT_URL = getenv('VAULT_URL', 'http://localhost:8200')
VAULT_SECRETS_PATH = getenv('VAULT_SECRETS_PATH', '')
# Vault settings for merchant api security credential storage
VAULT_TOKEN = getenv('VAULT_TOKEN', 'myroot')

MAX_SELENIUM_BROWSERS = getenv('MAX_SELENIUM_BROWSERS', '5')
SELENIUM_BROWSER_TIMEOUT = getenv('SELENIUM_BROWSER_TIMEOUT', '300')

BACK_OFF_COOLDOWN = 120

HERMES_CONFIRMATION_TRIES = 10

ENABLE_ICELAND_VALIDATE = getenv('ENABLE_ICELAND_VALIDATE', default="false")

BINK_CLIENT_ID = 'MKd3FfDGBi1CIUQwtahmPap64lneCa2R6GvVWKg6dNg4w9Jnpd'

# Prometheus settings
PUSH_PROMETHEUS_METRICS = getenv('PUSH_PROMETHEUS_METRICS', default="true")
PROMETHEUS_PUSH_GATEWAY = 'http://localhost:9100'
PROMETHEUS_JOB = 'midas'

API_AUTH_ENABLED = getenv("TXM_API_AUTH_ENABLED", default="true")
