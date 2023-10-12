from typing import Any, Type, cast

import kombu
import sentry_sdk
from kombu.mixins import ConsumerMixin
from olympus_messaging import JoinApplication, LoyaltyCardRemovedBink, Message, MessageDispatcher, build_message

import settings
from app import db
from app.db import redis_raw
from app.exceptions import BaseError
from app.journeys.removed import attempt_loyalty_card_removed
from app.reporting import get_logger
from app.retry_util import create_task, enqueue_retry_task
from app.scheme_account import JourneyTypes, SchemeAccountStatus

log = get_logger("task-consumer")


class TaskConsumer(ConsumerMixin):
    loyalty_request_queue = kombu.Queue(settings.LOYALTY_REQUEST_QUEUE)

    def __init__(self, connection: kombu.Connection) -> None:
        self.connection = connection
        self.dispatcher = MessageDispatcher()

        # When dispatching a new message add below a mapping to an on message receive method:
        self.dispatcher.connect(JoinApplication, self.on_join_application)
        self.dispatcher.connect(LoyaltyCardRemoved, self.on_loyalty_card_removed)

    def get_consumers(self, Consumer: Type[kombu.Consumer], channel: Any) -> list[kombu.Consumer]:  # pragma: no cover
        log.debug(f"{Consumer} has been retrieved")
        return [Consumer(queues=[self.loyalty_request_queue], callbacks=[self.on_message])]

    def on_message(self, body: dict, message: kombu.Message) -> None:  # pragma: no cover
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
                log.debug(f"Join request created for {user_info['scheme_account_id']}")
                session.commit()

        except BaseError as e:
            sentry_sdk.capture_exception(e)
            return

    @staticmethod
    def on_loyalty_card_removed(message: Message) -> None:
        try:
            message = cast(LoyaltyCardRemovedBink, message)
            scheme_slug = message.loyalty_plan
            status = int(message.message_data.get("status", 0))

            user_info = {
                "user_set": message.bink_user_id,
                "bink_user_id": message.bink_user_id,
                "scheme_account_id": int(message.request_id),
                "channel": message.channel,
                "status": status,
                "account_id": message.account_id,  # merchant's main answer from hermes eg card number
                "message_uid": message.transaction_id,
                "credentials": {},
                "journey_type": JourneyTypes.REMOVED.value,
                "origin": message.origin
            }
            attempt_loyalty_card_removed(scheme_slug, user_info)
            log.debug(f"Card removed for {user_info['scheme_account_id']}")
        except BaseError as e:
            sentry_sdk.capture_exception(e)
            return
