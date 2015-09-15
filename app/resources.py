import settings
import simplejson

from app import app, active
from app import retry
from tests.service.logins import CREDENTIALS
from app.agents.exceptions import LoginError, MinerError, STATUS_ACCOUNT_LOCKED, errors
from app.utils import resolve_agent
from app.encoding import JsonEncoder
from flask import url_for, make_response
from flask_restful import Resource, Api, abort
from flask_restful_swagger import swagger

api = swagger.docs(Api(app), apiVersion='1', api_spec_url="/api/v1/spec")


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
            return create_response(agent_instance.balance())
        except MinerError as e:
            abort(e.code, message=str(e))
        except Exception as e:
            abort(520, message=str(e))


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
            return create_response(agent_instance.transactions())
        except MinerError as e:
            abort(e.code, message=str(e))
        except Exception as e:
            abort(520, message=str(e))


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

        try:
            return create_response(agent_instance.account_overview())
        except MinerError as e:
            abort(e.code, message=str(e))
        except Exception as e:
            abort(520, message=str(e))


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
    response = make_response(simplejson.dumps(response_data, cls=JsonEncoder), 200)
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
            abort(e.code, message=str(e))
        retry.inc_count(key, retry_count, exists)
        abort(e.code, message=str(e))
    except Exception as e:
        abort(520, message=str(e))

    return agent_instance


