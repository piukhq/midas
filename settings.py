import os
import logging
import graypy
from app import AgentException
from environment import env_var, read_env

read_env()

logger = logging.getLogger('midas_logger')
logger.setLevel(logging.DEBUG)
focus_logger = True

GRAYLOG_HOST = env_var('GRAYLOG_HOST')
if GRAYLOG_HOST:
    handler = graypy.GELFHandler(GRAYLOG_HOST, 12201)
    logger.addHandler(handler)
elif focus_logger:
    handler_loc = logging.FileHandler('/var/tmp/midas_focus.log')
    logger.addHandler(handler_loc)


SLACK_API_KEY = "xoxp-10814716850-10810422998-11484111571-159b7e873a"
JUNIT_XML_FILENAME = "test_results.xml"

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("MIDAS_DEBUG", False)
LOCAL = env_var("MIDAS_LOCAL", False)
AES_KEY = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"

REDIS_URL = env_var("MIDAS_REDIS_URI", "redis://localhost:6379/0")

HADES_URL = env_var("HADES_URL", "http://local.hades.chingrewards.com:8000")

HERMES_URL = env_var("HERMES_URL", "http://local.hermes.chingrewards.com:8000")
APOLLO_URL = env_var("APOLLO_URL", "http://dev.apollo.loyaltyangels.local")
HEARTBEAT_URL = env_var("HEARTBEAT_URL", "https://hchk.io/22d1bb0c-daae-43db-8ab2-5a6da0c5f0ec")

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DNS = env_var("MIDAS_SENTRY_DNS", None)

RAVEN_IGNORE_EXCEPTIONS = [AgentException]
