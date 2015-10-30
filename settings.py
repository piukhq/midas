import os
from environment import env_var, read_env

read_env()

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("MIDAS_DEBUG", False)
LOCAL = env_var("MIDAS_LOCAL", False)
AES_KEY = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"

REDIS_URL = env_var("MIDAS_REDIS_URI", "redis://localhost:6379/0")

HADES_URL = env_var("HADES_URL", "http://local.hades.chingrewards.com:8000")

HERMES_URL = env_var("HERMES_URL", "http://local.hermes.chingrewards.com:8000")

SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

SENTRY_DNS = env_var("MIDAS_SENTRY_DNS",
                     "http://8dac759f053a44f685d6d2a1227910b1:7d603ac97f664536a0a568a28de06f86@192.168.1.53:8999/3")
