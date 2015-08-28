from flask import request, url_for, make_response
from flask_restful import Resource, Api, abort
from app.active import AGENTS, CREDENTIALS
import settings
from flask_restful import Resource, Api
from app.agents.tesco import Tesco
from app import app, active
from app.agents.exceptions import LoginError, MinerError
from app import retry
import simplejson

api = Api(app)


class Balance(Resource):
    # noinspection PyUnboundLocalVariable

    #agent_class = resolve_class(agent)
    # args = request.args
    # credentials = args['credentials']
    # api_key = args['api_key']

    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            # We can do some pretty printing or rendering in here
            pass

        # TODO: Resolve class in function
        try:
            agent_class = AGENTS[agent]
        except IndexError:
            abort(404, message='Agent does not exist')

        credentials = CREDENTIALS[agent]
        key = retry.get_key('tescos', credentials['user_name'])
        exists, retry_count = retry.get_count(key)

        # TODO: HANDLE THESE ERROR BY RETURNING ERROR CODES

        try:
            agent_class_instance = agent_class(credentials, 1)
        except LoginError as e:
            retry.inc_count(key, retry_count, exists)
        except MinerError as e:
            pass

        response_data = agent_class_instance.balance()
        return make_response(simplejson.dumps(response_data), 200)

api.add_resource(Balance, '/<string:agent>/balance/', endpoint="api.points_balance")


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


api.add_resource(Init, '/')


def example():
    credentials = active.CREDENTIALS['tesco']
    key = retry.get_key('tescos', credentials['user_name'])
    exists, retry_count = retry.get_count(key)

    try:
        b = Tesco(credentials, retry_count)
    except LoginError as e:
        retry.inc_count(key, retry_count, exists)
    except MinerError as e:
        pass


api.add_resource(Balance, '/balance')
