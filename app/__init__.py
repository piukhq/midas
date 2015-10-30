import logging
from flask import Flask
from app.retry import redis
from raven.contrib.flask import Sentry
import settings

sentry = Sentry()


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)
    if not settings.LOCAL:
        sentry.init_app(app, dsn=settings.SENTRY_DNS,
                        logging=True, level=logging.ERROR)
    api.init_app(app)
    redis.init_app(app)
    return app


