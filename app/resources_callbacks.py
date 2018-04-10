from flask import request
from flask_restful import Resource

from app import retry
from app.encryption import hash_ids
from app.resources import get_agent_class, create_response


class JoinCallback(Resource):

    def post(self, scheme_slug):
        hashed_record_uid = request.get_json()['record_uid']
        record_uid = hash_ids.decode(hashed_record_uid)[0]

        agent_class = get_agent_class(scheme_slug)

        key = retry.get_key(agent_class.__name__, record_uid)
        retry_count = retry.get_count(key)
        agent_instance = agent_class(retry_count, record_uid, scheme_slug=scheme_slug)

        agent_instance.register(request, inbound=True)

        return create_response({'success': True})
