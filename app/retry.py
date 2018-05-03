"""
Handle our persistence of the retry counts
"""
from flask.ext.redis import FlaskRedis

redis = FlaskRedis()


def get_count(key):
    retry_count = redis.get(key)
    if retry_count:
        return int(retry_count)
    return 0


def max_out_count(key, max_retries):
    redis.setex(key, max_retries, 60*15)


def inc_count(key):
    redis.incr(key)


def get_key(agent, user_name):
    return "retry-{0}-{1}".format(agent, user_name).lower()
