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

#We could create some sort of base request as balance and transactions are almost identical

class Balance(Resource):
    # noinspection PyUnboundLocalVariable
    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            # We can do some pretty printing or rendering in here
            pass
        try:
            credentials = CREDENTIALS[agent]
        except KeyError:
            abort(404, message='Credentials not present.')

        try:
            agent_class = resolve_agent(agent)
        except KeyError:
            abort(404, message='No such agent')

        agent_instance = agent_login(agent_class, credentials)

        response_data = agent_instance.balance()
        return make_response(simplejson.dumps(response_data), 200)

api.add_resource(Balance, '/<string:agent>/balance/', endpoint="api.points_balance")


class Transactions(Resource):
    # noinspection PyUnboundLocalVariable
    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            # We can do some pretty printing or rendering in here
            pass
        try:
            credentials = CREDENTIALS[agent]
        except KeyError:
            abort(404, message='Credentials not present.')

        try:
            agent_class = resolve_agent(agent)
        except KeyError:
            abort(404, message='No such agent')

        agent_instance = agent_login(agent_class, credentials)
        response_data = agent_instance.transactions()

        #TODO: ARROW IS NOT SERIALIZABLE
        return make_response(simplejson.dumps(response_data, cls=ArrowEncoder), 200)

api.add_resource(Transactions, '/<string:agent>/transactions/', endpoint="api.transactions")


class AccountOverview(Resource):
    # noinspection PyUnboundLocalVariable
    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            # We can do some pretty printing or rendering in here
            pass
        try:
            credentials = CREDENTIALS[agent]
        except KeyError:
            abort(404, message='Credentials not present.')

        try:
            agent_class = resolve_agent(agent)
        except KeyError:
            abort(404, message='No such agent')

        agent_instance = agent_login(agent_class, credentials)
        response_data = agent_instance.account_overview()

        #TODO: ARROW IS NOT SERIALIZABLE
        return make_response(simplejson.dumps(response_data, cls=ArrowEncoder), 200)

api.add_resource(AccountOverview, '/<string:agent>/account_overview/', endpoint="api.account_overview")


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


def agent_login(agent_class, credentials):
    key = retry.get_key('tesco', credentials['user_name'])
    exists, retry_count = retry.get_count(key)

    agent_instance = agent_class(retry_count)
    # TODO: HANDLE THESE ERROR BY RETURNING ERROR CODES
    try:
        agent_instance.attempt_login(credentials)
    except LoginError as e:
        if e.name == STATUS_ACCOUNT_LOCKED:
            retry.max_out_count(key, agent_instance.retry_limit)
        else:
            retry.inc_count(key, retry_count, exists)
    except MinerError as e:
        pass

    return agent_instance
