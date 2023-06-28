from typing import Any, Type, cast

import kombu
import sentry_sdk
from kombu.mixins import ConsumerMixin
from olympus_messaging import JoinApplication, LoyaltyCardRemovedBink, Message, MessageDispatcher, build_message
from werkzeug.exceptions import NotFound

import settings
from app import db
from app.db import redis_raw
from app.exceptions import BaseError
from app.journeys.common import get_agent_class
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
        self.dispatcher.connect(LoyaltyCardRemovedBink, self.on_loyalty_card_removed_bink)

    def get_consumers(self, Consumer: Type[kombu.Consumer], channel: Any) -> list[kombu.Consumer]:  # pragma: no cover
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
                session.commit()

        except BaseError as e:
            sentry_sdk.capture_exception(e)
            return

    @staticmethod
    def on_loyalty_card_removed_bink(message: Message) -> None:
        message = cast(LoyaltyCardRemovedBink, message)
        scheme_slug = message.loyalty_plan

        user_info = {
            "user_set": message.bink_user_id,
            "bink_user_id": message.bink_user_id,
            "scheme_account_id": int(message.request_id),
            "channel": message.channel,
            "account_id": message.account_id,  # merchant's main answer from hermes eg card number
            "message_uid": message.transaction_id,
            "credentials": {},
            "journey_type": JourneyTypes.JOIN.value   # maybe we need another type? Decide on 1st implementation
        }

        try:
            agent_class = get_agent_class(scheme_slug)
            if callable(getattr(agent_class, "loyalty_card_removed_bink", None)):
                # loyalty_card_removed_bink is not in base class so this will only work for agents which have
                # this method. This is a rough suggestion it may need work when implementing a solution ie is
                # login needed
                agent_instance = agent_class(1, user_info, scheme_slug)
                agent_instance.loyalty_card_removed_bink()
            else:
                log.warning(f"Loyalty cards removed bink has not been implemented for {scheme_slug}  info: {user_info}")
        except NotFound:
            log.warning(f"Trying to report loyalty cards removed bink: {scheme_slug} not found")
