import sentry_sdk
from celery import Celery
from flask import Flask, jsonify

from app.exceptions import AgentException, UnknownException
from app.prometheus import PrometheusManager

import settings
from app.retry import redis

celery = Celery(broker=settings.CELERY_BROKER_URL, config_source=settings)
prometheus_manager = PrometheusManager()


def create_app(config_name="settings"):
    from app.urls import api

    app = Flask("core")
    app.config.from_object(config_name)

    api.init_app(app)
    redis.init_app(app)

    @app.errorhandler(AgentException)
    def agent_error_request_handler(error):
        error = error.args[0]
        settings.logger.exception(error.message)

        response = jsonify({"message": error.message, "code": error.code, "name": error.name})
        response.status_code = error.code
        return response

    @app.errorhandler(UnknownException)
    def agent_unknown_request_handler(error):
        sentry_sdk.capture_exception(error)  # As this is an UNKNOWN error, also log to sentry

        response = jsonify({"message": str(error), "code": 520, "name": "Unknown Error"})
        response.status_code = 520
        return response

    return app
