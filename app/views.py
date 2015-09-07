import settings
import simplejson

from app import app, active
from app import retry
from tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError, MinerError, STATUS_ACCOUNT_LOCKED
from app.utils import resolve_agent, ArrowEncoder
from flask import url_for, make_response
from flask_restful import Resource, Api, abort

api = Api(app)

# We could create some sort of base request as balance and transactions are almost identical

class Balance(Resource):
    def get(self, agent_slug):
        agent_class = get_agent_class(agent_slug)
        credentials = get_credentials(agent_slug)
        agent_instance = agent_login(agent_class, credentials)

        return create_response(agent_instance.balance())

api.add_resource(Balance, '/<string:agent>/balance/', endpoint="api.points_balance")


class Transactions(Resource):
    def get(self, agent_slug):
        agent_class = get_agent_class(agent_slug)
        credentials = get_credentials(agent_slug)

        agent_instance = agent_login(agent_class, credentials)
        response_data = agent_instance.transactions()

        return create_response(response_data)

api.add_resource(Transactions, '/<string:agent>/transactions/', endpoint="api.transactions")


class AccountOverview(Resource):
    def get(self, agent_slug):
        agent_class = get_agent_class(agent_slug)
        credentials = get_credentials(agent_slug)
        agent_instance = agent_login(agent_class, credentials)
        response_data = agent_instance.account_overview()

        return create_response(response_data)


api.add_resource(AccountOverview, '/<string:agent_slug>/account_overview/', endpoint="api.account_overview")


class Init(Resource):
    def get(self):
        agents = []
        # Not all services will provide points and transactions
        # TODO: we should detect this dynamically
        for agent in active.AGENTS:
            agents.append({
                'name': agent[0],
                'services': {
                    'points': url_for('api.points_balance', id=agent[0]),
                    'transactions': '',
                    'pointsAndTransactions': ''
                }
            })

        response_data = {'agents': agents}
        return response_data


api.add_resource(Init, '/agents/')


def create_response(response_data):
    response = make_response(simplejson.dumps(response_data, cls=ArrowEncoder), 200)
    response.headers['Content-Type'] = "application/json"
    return response


def get_agent_class(agent_slug):
    if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
        # We can do some pretty printing or rendering in here
        pass
    try:
        return resolve_agent(agent_slug)
    except KeyError:
        abort(404, message='No such agent')


def get_credentials(agent_slug):
    try:
        return CREDENTIALS[agent_slug]
    except KeyError:
        abort(400, message='Credentials not present.')


def agent_login(agent_class, credentials):
    key = retry.get_key('tesco', credentials.get('user_name') or credentials.get('card_number'))
    exists, retry_count = retry.get_count(key)

    agent_instance = agent_class(retry_count)
    try:
        agent_instance.attempt_login(credentials)
    except LoginError as e:
        if e.name == STATUS_ACCOUNT_LOCKED:
            retry.max_out_count(key, agent_instance.retry_limit)
            abort(429, message=e.name)

        retry.inc_count(key, retry_count, exists)
        abort(400, message=e.name)
    except MinerError as e:
        abort(400, message=e.name)
    except Exception as e:
        abort(400, message=str(e))

    return agent_instance
