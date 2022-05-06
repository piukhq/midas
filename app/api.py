from celery import Celery
from flask import Flask, jsonify

import settings
from app.audit import AuditLogger
from app.exceptions import BaseError
from app.prometheus import PrometheusManager
from app.reporting import get_logger

celery = Celery(broker=settings.broker_url, config_source=settings)
prometheus_manager = PrometheusManager()
audit_logger = AuditLogger()

log = get_logger("api")


def create_app(config_name="settings"):
    from app.urls import api

    app = Flask("core")
    app.config.from_object(config_name)

    api.init_app(app)

    @app.errorhandler(BaseError)
    def agent_error_request_handler(error):
        error = error.args[0]
        log.warning(error.message)

        response = jsonify({"message": error.message, "code": error.code, "name": error.name})
        response.status_code = error.code
        return response

    return app
