from flask_restful import Resource

from app import retry, AgentException, UnknownException
from app.agents.exceptions import AgentError
from app.configuration import Configuration
from app.encryption import hash_ids
from app.resources import get_agent_class, create_response
from app.security.utils import authorise


class JoinCallback(Resource):

    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        user_info = {
            'credentials': None,
            'status': 'PENDING',
            'scheme_account_id': hash_ids.decode(data['record_uid'])[0]
        }
        try:
            agent_class = get_agent_class(scheme_slug)

            key = retry.get_key(agent_class.__name__, user_info['scheme_account_id'])
            retry_count = retry.get_count(key)
            agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug, config=config)

            agent_instance.register(data, inbound=True)
        except AgentError as e:
            raise AgentException(e)
        except Exception as e:
            raise UnknownException(e)

        return create_response({'success': True})
