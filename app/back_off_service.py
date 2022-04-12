import time

from redis import Redis

from app.redis_retry import redis_connection
from settings import REDIS_URL


class BackOffService:
    def __init__(self):
        """
        Connect to the Redis database containing merchant API cool downs.
        """
        self.storage = Redis.from_url(REDIS_URL)

    @redis_connection
    def is_on_cooldown(self, scheme_slug, handler_type):
        current_datetime = time.time()
        expiry_datetime = self.storage.get("back-off:{}:{}".format(scheme_slug, handler_type))

        return current_datetime < float(expiry_datetime) if expiry_datetime else None

    @redis_connection
    def activate_cooldown(self, scheme_slug, handler_type, cooldown_time):
        expiry_date = time.time() + cooldown_time
        self.storage.set("back-off:{}:{}".format(scheme_slug, handler_type), expiry_date)
