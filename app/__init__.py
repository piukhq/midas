from flask import Flask
from app.retry import redis


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    api.init_app(app)
    redis.init_app(app)
    return app


