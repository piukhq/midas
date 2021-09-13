import kombu
from olympus_messaging import Message

import settings
from app.reporting import get_logger

log = get_logger("messaging")


def _on_error(exc, interval):
    log.warning(f"Failed to connect to RabbitMQ: {exc}. Will retry after {interval:.1f}s...")


def enqueue_request(message: Message) -> None:
    with kombu.Connection(settings.AMQP_DSN) as conn:
        conn.ensure_connection(
            errback=_on_error, max_retries=3, interval_start=0.2, interval_step=0.4, interval_max=1, timeout=3
        )
        q = conn.SimpleQueue(settings.LOYALTY_REQUEST_QUEUE)
        q.put(message.body, headers=message.properties)
