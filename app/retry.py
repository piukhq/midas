"""
Handle our persistence of the retry counts
"""
from app import redis


def get_count(key):
    retry_count = redis.get(key)
    if retry_count:
        return True, int(retry_count)
    return False, 0


def inc_count(key, retry_count, exists):
    redis.set(key, retry_count + 1)
    if not exists:
        redis.expire(key, 60*15)


def get_key(agent, user_name):
    return "retry-{0}-{1}".format(agent, user_name)
