import logging

from flask import Flask, jsonify
from raven.contrib.flask import Sentry
from app.exceptions import AgentException, UnknownException
from app.retry import redis
from app.version import __version__
from celery import Celery
import settings


sentry = Sentry()
celery = None


def make_celery(app):
    celery_app = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery_app.conf.update(app.config)
    TaskBase = celery_app.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app


def create_app(config_name="settings"):
    from app.urls import api
    app = Flask('core')
    app.config.from_object(config_name)
    if settings.SENTRY_DSN:
        sentry.init_app(
            app,
            dsn=settings.SENTRY_DSN,
            logging=True,
            level=logging.ERROR)
        sentry.client.release = __version__
    api.init_app(app)
    redis.init_app(app)
    global celery
    celery = make_celery(app)



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


if celery is None:
    create_app()


@celery.task
def test_celery():
    print("test celery")
