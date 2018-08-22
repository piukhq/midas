from flask_restful import Resource

from app import retry, AgentException, UnknownException, sentry
from app.agents.exceptions import AgentError
from app.configuration import Configuration
from app.encryption import hash_ids
from app.resources import get_agent_class, create_response
from app.scheme_account import update_pending_join_account
from app.utils import SchemeAccountStatus, JourneyTypes
from app.security.utils import authorise


class JoinCallback(Resource):

    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        try:
            message_uid = data['message_uid']
            scheme_account_id = hash_ids.decode(data['record_uid'])
            if not scheme_account_id:
                raise ValueError('record_uid not valid')

            user_info = {
                'credentials': None,
                'status': SchemeAccountStatus.PENDING,
                'scheme_account_id': scheme_account_id[0],
                'journey_type': JourneyTypes.JOIN.value
            }
        except (KeyError, ValueError) as e:
            raise UnknownException(e)

        try:
            agent_class = get_agent_class(scheme_slug)

            key = retry.get_key(agent_class.__name__, user_info['scheme_account_id'])
            retry_count = retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)

            agent_instance.register(data, inbound=True)
        except AgentError as e:
            update_pending_join_account(user_info['scheme_account_id'], str(e), message_uid, raise_exception=False)
            sentry.captureException(e)
            raise AgentException(e)
        except Exception as e:
            update_pending_join_account(user_info['scheme_account_id'], str(e), message_uid, raise_exception=False)
            raise UnknownException(e)

        return create_response({'success': True})
