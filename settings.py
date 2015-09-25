import os
from environment import env_var, read_env

read_env()

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("MIDAS_DEBUG", False)

AES_KEY = "6gZW4ARFINh4DR1uIzn12l7Mh1UF982L"

REDIS_URL = env_var("MIDAS_REDIS_URI", "redis://localhost:6379/0")

HADES_URL = env_var("HADES_URL", "http://local.hades.chingrewards.com:8000")