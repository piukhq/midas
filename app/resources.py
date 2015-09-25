import json
from flask import url_for, make_response
from flask_restful import Resource, Api, abort
from flask_restful_swagger import swagger
from app.exceptions import agent_abort, unknown_abort
import settings
from app import active, retry
from tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError, AgentError, STATUS_ACCOUNT_LOCKED, errors
from app.utils import resolve_agent
from app.encoding import JsonEncoder
from app.publish import Publish

api = swagger.docs(Api(), apiVersion='1', api_spec_url="/api/v1/spec")


class Balance(Resource):
    @swagger.operation(
        responseMessages=list(errors.values()),
        notes="Return a users balance for a specific agent"
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = get_credentials(scheme_slug)
        agent_instance = agent_login(agent_class, credentials)

        try:
            balance = agent_instance.balance()
            Publish().balance(balance)
            return create_response(balance)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(Balance, '/<string:scheme_slug>/balance/', endpoint="api.points_balance")


class Transactions(Resource):
    @swagger.operation(
        responseMessages=list(errors.values()),
        notes="Return a users latest transactions for a specific agent"
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = get_credentials(scheme_slug)
        agent_instance = agent_login(agent_class, credentials)

        try:
            transactions = agent_instance.transactions()
            Publish().transactions(transactions)
            return create_response(transactions)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(Transactions, '/<string:scheme_slug>/transactions/', endpoint="api.transactions")


class AccountOverview(Resource):
    """Return both a users balance and latest transaction for a specific agent"""
    @swagger.operation(
        responseMessages=list(errors.values())
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = get_credentials(scheme_slug)
        agent_instance = agent_login(agent_class, credentials)

        publish = Publish()

        try:
            account_overview = agent_instance.account_overview()
            publish.balance(account_overview.balance)
            publish.transactions(account_overview.transactions)
            return create_response(account_overview)
        except AgentError as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(AccountOverview, '/<string:scheme_slug>/account_overview/', endpoint="api.account_overview")


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
    response = make_response(json.dumps(response_data, cls=JsonEncoder), 200)
    response.headers['Content-Type'] = "application/json"
    return response


def get_agent_class(scheme_slug):
    if settings.DEBUG and 'text/html' == api.mediatypes()[0]:
        # We can do some pretty printing or rendering in here
        pass
    try:
        return resolve_agent(scheme_slug)
    except KeyError:
        abort(404, message='No such agent')


def get_credentials(scheme_slug):
    try:
        return CREDENTIALS[scheme_slug]
    except KeyError:
        abort(401, message='Credentials not present.')


def agent_login(agent_class, credentials):
    user_name = credentials.get('user_name') or credentials.get('card_number')
    key = retry.get_key(agent_class.__name__, user_name)
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


