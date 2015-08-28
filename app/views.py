from app import app, active
from flask import request, url_for
from flask_restful import Resource, Api, abort
from app.active import AGENTS
import settings

api = Api(app)


class Balance(Resource):
    # noinspection PyUnboundLocalVariable
    def get(self, agent):
        if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
            print(True)
        try:
            agent_class = AGENTS[agent](credentials={})
        except IndexError:
            abort(404, message='Agent does not exist')

        points_balance = agent_class.points()
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