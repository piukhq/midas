from flask import request, url_for
from flask_restful import Resource, Api, abort
from app.active import AGENTS, CREDENTIALS
import settings
from flask_restful import Resource, Api
from app.agents.tesco import Tesco
from app import app, active
from app.agents.exceptions import LoginError, MinerError
from app import retry


api = Api(app)


class Balance(Resource):
    # noinspection PyUnboundLocalVariable
    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            print(True)
        # TODO: Resolve class in function
        try:
            agent_class = AGENTS[agent]
        except IndexError:
            abort(404, message='Agent does not exist')

        agent_class_instance = agent_class(credentials=CREDENTIALS[AGENTS])
        points_balance = agent_class_instance.points()
        return {'points': points_balance}

        #agent_class = resolve_class(agent)
        # args = request.args
        # credentials = args['credentials']
        # api_key = args['api_key']


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
    key = retry.get_key('tesos', credentials['user_name'])
    exists, retry_count = retry.get_count(key)

    try:
        b = Tesco(credentials, retry_count)
    except LoginError as e:
        retry.inc_count(key, retry_count, exists)
    except MinerError as e:
        pass


api.add_resource(Balance, '/balance')
