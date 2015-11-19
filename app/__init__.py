import logging
from flask import Flask, jsonify

from app.exceptions import AgentException
from app.retry import redis
from raven.contrib.flask import Sentry
import settings

sentry = Sentry()


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)
    if settings.SENTRY_DNS:
        sentry.init_app(app, dsn=settings.SENTRY_DNS, logging=True, level=logging.ERROR)
    api.init_app(app)
    redis.init_app(app)

    @app.errorhandler(AgentException)
    def bad_request_handler(error):
        response = jsonify({'message': error.description, 'code': error.code, 'name': error.name})
        response.status_code = error.code
        return response

    return app
