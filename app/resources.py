import json
from flask import make_response, request
from flask_restful import Resource, Api, abort
from flask_restful_swagger import swagger
from app.exceptions import agent_abort, unknown_abort
import settings
from app import retry
from app.agents.exceptions import LoginError, AgentError, STATUS_ACCOUNT_LOCKED, errors
from app.utils import resolve_agent
from app.encoding import JsonEncoder
from app.publish import Publish
from app.encyption import AESCipher

api = swagger.docs(Api(), apiVersion='1', api_spec_url="/api/v1/spec")

scheme_account_id_doc = {
    "name": "scheme_account_id",
    "required": True,
    "dataType": "integer",
    "paramType": "query"
}
user_id_doc = {
    "name": "user_id",
    "required": True,
    "dataType": "integer",
    "paramType": "query"
}
credentials_doc = {
    "name": "credentials",
    "required": True,
    "dataType": "string",
    "paramType": "query"
}


class Balance(Resource):
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
        notes="Return a users balance for a specific agent"
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = decrypt_credentials(request.args['credentials'])

        agent_instance = agent_login(agent_class, credentials)

        try:
            balance = agent_instance.balance()
            balance['scheme_account_id'] = int(request.args['scheme_account_id'])
            balance['user_id'] = int(request.args['user_id'])
            Publish().balance(balance)
            return create_response(balance)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(Balance, '/<string:scheme_slug>/balance', endpoint="api.points_balance")


class Transactions(Resource):
    @swagger.operation(
        responseMessages=list(errors.values()),
        notes="Return a users latest transactions for a specific agent",
        parameters=[scheme_account_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)

        credentials = decrypt_credentials(request.args['credentials'])
        agent_instance = agent_login(agent_class, credentials)

        try:
            transactions = agent_instance.transactions()
            transactions = update_transactions(transactions, int(request.args['scheme_account_id']))

            Publish().transactions(transactions)
            return create_response(transactions)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(Transactions, '/<string:scheme_slug>/transactions', endpoint="api.transactions")


class AccountOverview(Resource):
    """Return both a users balance and latest transaction for a specific agent"""
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = decrypt_credentials(request.args['credentials'])
        agent_instance = agent_login(agent_class, credentials)

        publish = Publish()

        try:
            account_overview = agent_instance.account_overview()

            balance = account_overview["balance"]
            balance['scheme_account_id'] = int(request.args['scheme_account_id'])
            balance['user_id'] = int(request.args['user_id'])

            publish.balance(balance)

            transactions = account_overview["transactions"]
            transactions = update_transactions(transactions, int(request.args['scheme_account_id']))
            publish.transactions(transactions)
            return create_response(account_overview)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(AccountOverview, '/<string:scheme_slug>/account_overview', endpoint="api.account_overview")


def update_transactions(transactions, scheme_account_id):
    for transaction in transactions:
        transaction['scheme_account_id'] = scheme_account_id
    return transactions


def decrypt_credentials(credentials):
    aes = AESCipher(settings.AES_KEY.encode())
    return json.loads(aes.decrypt(credentials.replace(" ", "+")))


def create_response(response_data):
    response = make_response(json.dumps(response_data, cls=JsonEncoder), 200)
    response.headers['Content-Type'] = "application/json"
    return response


def get_agent_class(scheme_slug):
    try:
        return resolve_agent(scheme_slug)
    except KeyError:
        abort(404, message='No such agent')


def agent_login(agent_class, credentials):
    user_name_key = credentials.get('user_name') or credentials.get('card_number')
    key = retry.get_key(agent_class.__name__, user_name_key)
    exists, retry_count = retry.get_count(key)

    agent_instance = agent_class(retry_count)
    try:
        agent_instance.attempt_login(credentials)
    except LoginError as e:
        if e.name == STATUS_ACCOUNT_LOCKED:
            retry.max_out_count(key, agent_instance.retry_limit)
            agent_abort(e)
        retry.inc_count(key, retry_count, exists)
        agent_abort(e)
    except Exception as e:
        unknown_abort(e)

    return agent_instance


