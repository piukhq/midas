from typing import Any, Type, cast

import kombu
from kombu.mixins import ConsumerMixin
from olympus_messaging import JoinApplication, Message, MessageDispatcher, build_message

import settings
from app.exceptions import AgentException
from app.journeys.join import attempt_join
from app.reporting import get_logger
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
            attempt_join(message.loyalty_plan, user_info, message.transaction_id)
        except AgentException as ex:  # we don't want AgentExceptions to go to Sentry
            log.warning(f"attempt_join raised {repr(ex)}")
            return
