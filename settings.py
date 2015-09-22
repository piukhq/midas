import os
from environment import env_var

SECRET_KEY = 'QlLWJYCugcMQ59nIWh5lnHBMcgHtLupJrv4SvohR'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("MIDAS_DEBUG", False)


REDIS_URL = env_var("MIDAS_REDIS_URI", "redis://localhost:6379/0")