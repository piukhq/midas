import json
from typing import Any, Type, cast

import kombu
from kombu.mixins import ConsumerMixin
from olympus_messaging import JoinApplication, Message, MessageDispatcher, build_message
from retry_tasks_lib.utils.synchronous import enqueue_retry_task, sync_create_task

import settings
from app.db import db_session
from app.reporting import get_logger
from app.retry_worker import redis_raw
from app.scheme_account import JourneyTypes, SchemeAccountStatus

log = get_logger("task-consumer")


class TaskConsumer(ConsumerMixin):
    loyalty_request_queue = kombu.Queue(settings.LOYALTY_REQUEST_QUEUE)

    def __init__(self, connection: kombu.Connection) -> None:
        self.connection = connection
        self.dispatcher = MessageDispatcher()
        self.dispatcher.connect(JoinApplication, self.on_join_application)

    def get_consumers(self, Consumer: Type[kombu.Consumer], channel: Any) -> list[kombu.Consumer]:
        return [Consumer(queues=[self.loyalty_request_queue], callbacks=[self.on_message])]

    def on_message(self, body: dict, message: kombu.Message) -> None:
        try:
            self.dispatcher.dispatch(build_message(message.headers, body))
        finally:
            message.ack()

    def on_join_application(self, message: Message) -> None:
        message = cast(JoinApplication, message)
        user_info = {
            "user_set": message.bink_user_id,
            "credentials": message.join_data,
            "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,  # TODO: check where/how this is used
            "journey_type": JourneyTypes.JOIN.value,
            "scheme_account_id": int(message.request_id),
            "channel": message.channel,
        }

        try:
            task = sync_create_task(
                db_session=db_session,
                task_type_name="attempt-join",
                params={
                    "scheme_slug": message.loyalty_plan,
                    "user_info": json.dumps(user_info),
                    "tid": message.transaction_id,
                },
            )
            with db_session:
                enqueue_retry_task(connection=redis_raw, retry_task=task)
                db_session.commit()

        except BaseException as ex:  # we don't want AgentExceptions to go to Sentry
            log.warning(f"attempt_join raised {repr(ex)}")
            return
