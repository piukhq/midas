"""
Handle our persistence of the retry counts
"""
from functools import wraps

import redis.exceptions as redis_exceptions
from redis import Redis

import settings
from app.exceptions import ServiceConnectionError

redis = Redis.from_url(settings.REDIS_URL)


def redis_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis_exceptions.ConnectionError as e:
            raise ServiceConnectionError(response="Error connecting to Redis.") from e

    return wrapper


@redis_connection
def get_count(key):
    retry_count = redis.get(key)
    if retry_count:
        return int(retry_count)
    return 0


@redis_connection
def max_out_count(key, max_retries):
    redis.setex(key, 60 * 15, max_retries)


@redis_connection
def inc_count(key):
    redis.incr(key)


def get_key(agent, user_name):
    return "retry-{0}-{1}".format(agent, user_name).lower()
