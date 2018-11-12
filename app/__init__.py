import logging

from ddtrace import tracer
from ddtrace.contrib.flask import TraceMiddleware

from celery import Celery
from flask import Flask, jsonify
from raven.contrib.flask import Sentry

from app.exceptions import AgentException, UnknownException

import settings
from app.retry import redis
from app.version import __version__

sentry = Sentry()
celery = Celery(backend=settings.CELERY_RESULT_BACKEND, broker=settings.CELERY_BROKER_URL, config_source=settings)


def create_app(config_name="settings"):
    from app.urls import api
    app = Flask('core')
    app.config.from_object(config_name)

    TraceMiddleware(
        app,
        tracer,
        service="midas",
        distributed_tracing=True)

    app.config['SENTRY_CONFIG'] = {
        'ignore_exceptions': [AgentException, UnknownException],
    }
    if settings.SENTRY_DSN:
        sentry.init_app(
            app,
            dsn=settings.SENTRY_DSN,
            logging=True,
            level=logging.ERROR)
        sentry.client.release = __version__
    api.init_app(app)
    redis.init_app(app)

    @app.errorhandler(AgentException)
    def agent_error_request_handler(error):
        error = error.args[0]
        response = jsonify({'message': error.message, 'code': error.code, 'name': error.name})
        response.status_code = error.code
        return response

    @app.errorhandler(UnknownException)
    def agent_unknown_request_handler(error):
        response = jsonify({'message': str(error), 'code': 520, 'name': 'Unknown Error'})
        response.status_code = 520
        return response

    return app
