import kombu

import settings
from app.messaging.consumer import TaskConsumer


def main():
    with kombu.Connection(settings.AMQP_DSN) as conn:
        consumer = TaskConsumer(conn)
        consumer.run()


if __name__ == "__main__":
    main()
