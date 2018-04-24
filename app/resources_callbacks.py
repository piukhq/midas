import json

from flask_restful import Resource

from app import retry
from app.configuration import Configuration
from app.encryption import hash_ids
from app.resources import get_agent_class, create_response
from app.security import authorise


class JoinCallback(Resource):

    @authorise(Configuration.JOIN_HANDLER)
    def post(self, scheme_slug, data, config):
        hashed_record_uid = json.loads(data)['record_uid']
        scheme_account_id = hash_ids.decode(hashed_record_uid)[0]

        agent_class = get_agent_class(scheme_slug)

        key = retry.get_key(agent_class.__name__, scheme_account_id)
        retry_count = retry.get_count(key)
        agent_instance = agent_class(retry_count, scheme_account_id, scheme_slug=scheme_slug, config=config)

        agent_instance.register(data, inbound=True)

        return create_response({'success': True})
