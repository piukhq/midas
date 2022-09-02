from typing import Any, Type, cast

import kombu
import sentry_sdk
from kombu.mixins import ConsumerMixin
from olympus_messaging import JoinApplication, Message, MessageDispatcher, build_message

import settings
from app import db
from app.db import redis_raw
from app.exceptions import BaseError
from app.reporting import get_logger
from app.retry_util import create_task, enqueue_retry_task
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

        # Temporary check for deploying hermes to midas messaging for join.
        # Prevents the possibility that we have something on the message queue already and crashing.
        # Can be removed once hermes-midas messaging has been deployed to prod.
        try:
            credentials = message.join_data["encrypted_credentials"]
        except (KeyError, TypeError):
            credentials = message.join_data

        user_info = {
            "user_set": message.bink_user_id,
            "bink_user_id": message.bink_user_id,
            "credentials": credentials,
            "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,  # TODO: check where/how this is used
            "journey_type": JourneyTypes.JOIN.value,
            "scheme_account_id": int(message.request_id),
            "channel": message.channel,
        }
        try:
            with db.session_scope() as session:
                task = create_task(
                    db_session=session,
                    user_info=user_info,
                    journey_type="attempt-join",
                    message_uid=message.transaction_id,
                    scheme_identifier=message.loyalty_plan,
                    scheme_account_id=message.request_id,
                )
                enqueue_retry_task(connection=redis_raw, retry_task=task)
                session.commit()

        except BaseError as e:
            sentry_sdk.capture_exception(e)
            return
