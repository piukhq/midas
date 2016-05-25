import os
import logging
import graypy
from app import AgentException
from environment import env_var, read_env

read_env()

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

HADES_URL = env_var('HADES_URL', 'http://local.hades.chingrewards.com:8000')

HERMES_URL = env_var('HERMES_URL', 'http://local.hermes.chingrewards.com:8000')
APOLLO_URL = env_var('APOLLO_URL', 'http://dev.apollo.loyaltyangels.local')
HEARTBEAT_URL = env_var('HEARTBEAT_URL', 'https://hchk.io/22d1bb0c-daae-43db-8ab2-5a6da0c5f0ec')

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DNS = env_var('MIDAS_SENTRY_DNS', None)

RAVEN_IGNORE_EXCEPTIONS = [AgentException]

PROPAGATE_EXCEPTIONS = True

INFLUX_HOST = env_var('INFLUX_HOST', '192.168.1.53')
INFLUX_PORT = env_var('INFLUX_PORT', '8086')
INFLUX_USER = env_var('INFLUX_USER', 'root')
INFLUX_PASSWORD = env_var('INFLUX_PASSWORD', 'root')
INFLUX_DATABASE = env_var('INFLUX_DATABSE', 'test_results')

MAX_VALUE_LABEL_LENGTH = 11
