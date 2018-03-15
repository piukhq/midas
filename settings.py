import os
import logging
import graypy
from app import AgentException
from environment import env_var, read_env

read_env()

DEV_HOST = env_var('DEV_HOST', '0.0.0.0')
DEV_PORT = env_var('DEV_PORT', '8000')

logging.basicConfig(filename='merchant_api.log', level=logging.DEBUG)
logger = logging.getLogger('midas_logger')
logger.setLevel(logging.DEBUG)

GRAYLOG_HOST = env_var('GRAYLOG_HOST')
if GRAYLOG_HOST:
    handler = graypy.GELFHandler(GRAYLOG_HOST, 12201)
    logger.addHandler(handler)

SLACK_API_KEY = 'xoxp-10814716850-12751177555-33955253125-1750700274'
JUNIT_XML_FILENAME = 'test_results.xml'

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var('MIDAS_DEBUG', False)
LOCAL = env_var('MIDAS_LOCAL', False)
AES_KEY = '6gZW4ARFINh4DR1uIzn12l7Mh1UF982L'

REDIS_URL = env_var('MIDAS_REDIS_URI', 'redis://localhost:6379/0')
USER_TOKEN_REDIS_URL = env_var('USER_TOKEN_REDIS_URI', 'redis://localhost:6379/4')

HADES_URL = env_var('HADES_URL', 'http://local.hades.chingrewards.com:8000')

HERMES_URL = env_var('HERMES_URL', 'http://local.hermes.chingrewards.com:8000')
HELIOS_URL = env_var('HELIOS_URL', 'https://api.bink-dev.xyz/dashboard')
HEARTBEAT_URL = env_var('HEARTBEAT_URL', 'https://hchk.io/976b50d5-1616-4c7e-92ac-6e05e0916e82')

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DNS = env_var('MIDAS_SENTRY_DNS', None)

RAVEN_IGNORE_EXCEPTIONS = [AgentException]

PROPAGATE_EXCEPTIONS = True

INFLUX_HOST = env_var('INFLUX_HOST', '192.168.1.53')
INFLUX_PORT = env_var('INFLUX_PORT', '8086')
INFLUX_USER = env_var('INFLUX_USER', 'root')
INFLUX_PASSWORD = env_var('INFLUX_PASSWORD', 'root')
INFLUX_DATABASE = env_var('INFLUX_DATABASE', 'test_results')

MAX_VALUE_LABEL_LENGTH = 11
