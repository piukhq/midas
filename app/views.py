from flask_restful import Resource, Api
from app import app
from flask import request

api = Api(app)


class Balance(Resource):
    def get(self):
        args = request.args
        credentials = args['credentials']
        agent = args['agent']
        api_key = args['api_key']

        return {'hello': 'stuff'}


api.add_resource(Balance, '/balance')
