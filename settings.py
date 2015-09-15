import os


SECRET_KEY = 'xxxxx'

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = True


REDIS_URL = "redis://localhost:6379/0"