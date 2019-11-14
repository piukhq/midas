"""
Handle our persistence of the retry counts
"""
from functools import wraps

import redis.exceptions as redis_exceptions
from flask_redis import FlaskRedis

from app.agents.exceptions import AgentError, SERVICE_CONNECTION_ERROR

redis = FlaskRedis()


def redis_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis_exceptions.ConnectionError as e:
            raise AgentError(SERVICE_CONNECTION_ERROR, message="Error connecting to Redis.") from e
    return wrapper


@redis_connection
def get_count(key):
    retry_count = redis.get(key)
    if retry_count:
        return int(retry_count)
    return 0


@redis_connection
def max_out_count(key, max_retries):
    redis.setex(key, max_retries, 60 * 15)


@redis_connection
def inc_count(key):
    redis.incr(key)


def get_key(agent, user_name):
    return "retry-{0}-{1}".format(agent, user_name).lower()
