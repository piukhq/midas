import os
import logging
from app import AgentException
from environment import env_var, read_env


os.chdir(os.path.dirname(__file__))
read_env()

DEV_HOST = env_var('DEV_HOST', '0.0.0.0')
DEV_PORT = env_var('DEV_PORT', '8000')

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
DEBUG = env_var('MIDAS_DEBUG', False)
LOCAL = env_var('MIDAS_LOCAL', False)
AES_KEY = '6gZW4ARFINh4DR1uIzn12l7Mh1UF982L'

REDIS_PASSWORD = env_var('REDIS_PASSWORD', '')
REDIS_HOST = env_var('REDIS_HOST', 'localhost')
REDIS_PORT = env_var('REDIS_PORT', '6379')
REDIS_DB = env_var('REDIS_DB', '0')
REDIS_URL = 'redis://:{password}@{host}:{port}/{db}'.format(**{
    'password': REDIS_PASSWORD,
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'db': REDIS_DB
})

RETRY_PERIOD = env_var('RETRY_PERIOD', '1800')
REDIS_CELERY_DB = env_var('REDIS_CELERY_DB', '1')
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
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


HADES_URL = env_var('HADES_URL', 'http://local.hades.chingrewards.com:8000')
HERMES_URL = env_var('HERMES_URL', 'http://local.hermes.chingrewards.com:8000')
HELIOS_URL = env_var('HELIOS_URL', 'https://api.bink-dev.xyz/dashboard')
HEARTBEAT_URL = env_var('HEARTBEAT_URL', 'https://hchk.io/976b50d5-1616-4c7e-92ac-6e05e0916e82')
CONFIG_SERVICE_URL = env_var('CONFIG_SERVICE_URL', '')

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DSN = env_var('SENTRY_DSN')
RAVEN_IGNORE_EXCEPTIONS = [AgentException]

PROPAGATE_EXCEPTIONS = True

INFLUX_HOST = env_var('INFLUX_HOST', '192.168.1.53')
INFLUX_PORT = env_var('INFLUX_PORT', '8086')
INFLUX_USER = env_var('INFLUX_USER', 'root')
INFLUX_PASSWORD = env_var('INFLUX_PASSWORD', 'root')
INFLUX_DATABASE = env_var('INFLUX_DATABASE', 'test_results')

MAX_VALUE_LABEL_LENGTH = 11

# INTERCOM_TOKEN default value is for testing
INTERCOM_TOKEN = env_var('INTERCOM_TOKEN', 'dG9rOmE4MGYzNDRjX2U5YzhfNGQ1N184MTA0X2E4YTgwNDQ2ZGY1YzoxOjA=')
INTERCOM_HOST = 'https://api.intercom.io'
INTERCOM_EVENTS_PATH = 'events'

HELIOS_DB_URI = env_var('HELIOS_DB_URI', 'postgresql+psycopg2://helios:j8NUz3vzPSn$@10.0.104.22:5432/helios')

CREDENTIALS_LOCAL = env_var('CREDENTIALS_LOCAL', False)
LOCAL_CREDENTIALS_FILE = os.path.join(APP_DIR, 'app', 'tests', 'service', 'credentials', 'credentials.json')

VAULT_URL = env_var('VAULT_URL', 'http://localhost:8200')
# Vault settings for merchant api security credential storage
VAULT_TOKEN = env_var('VAULT_TOKEN', 'myroot')

MAX_SELENIUM_BROWSERS = env_var('MAX_SELENIUM_BROWSERS', '5')
SELENIUM_BROWSER_TIMEOUT = env_var('SELENIUM_BROWSER_TIMEOUT', '300')

BACK_OFF_COOLDOWN = 120
