import json
import functools
from flask.ext.restful.utils.cors import crossdomain
import settings

from app.exceptions import agent_abort, unknown_abort
from app import retry
from app.agents.exceptions import LoginError, AgentError, errors, RetryLimitError
from app.utils import resolve_agent
from app.encoding import JsonEncoder
from app import publish
from app.encryption import AESCipher
from app.publish import thread_pool_executor
from flask import make_response, request
from flask_restful import Resource, Api, abort
from flask_restful_swagger import swagger


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


def validate_parameters(method):
    """
    Checks swaggers defined parameters exist in query string
    """
    @functools.wraps(method)
    def f(*args, **kwargs):
        for parameter in method.__swagger_attr['parameters']:
            if not parameter["required"] or parameter["paramType"] != "query":
                continue
            if parameter["name"] not in request.args:
                abort(400, message="Missing required query parameter '{0}'".format(parameter["name"]))

        return method(*args, **kwargs)
    return f


class Balance(Resource):
    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
        notes="Return a users balance for a specific agent"
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = decrypt_credentials(request.args['credentials'])
        scheme_account_id = int(request.args['scheme_account_id'])
        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class, credentials, scheme_account_id)

        try:
            status = 1
            balance = publish.balance(agent_instance.balance(), scheme_account_id,  int(request.args['user_id']), tid)
            # Asynchronously get the transactions for the a user
            thread_pool_executor.submit(publish_transactions, agent_instance, scheme_account_id, tid)

            return create_response(balance)
        except (LoginError, AgentError) as e:
            status = e.code
            agent_abort(e)
        except Exception as e:
            status = 520
            unknown_abort(e)
        finally:
            thread_pool_executor.submit(publish.status, scheme_account_id, status, tid)


api.add_resource(Balance, '/<string:scheme_slug>/balance', endpoint="api.points_balance")


def publish_transactions(agent_instance, scheme_account_id, tid):
    transactions = agent_instance.transactions()
    publish.transactions(transactions, scheme_account_id, tid)


class Transactions(Resource):
    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        notes="Return a users latest transactions for a specific agent",
        parameters=[scheme_account_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        scheme_account_id = int(request.args['scheme_account_id'])
        credentials = decrypt_credentials(request.args['credentials'])
        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class, credentials, scheme_account_id)

        try:
            status = 1
            transactions = publish.transactions(agent_instance.transactions(), scheme_account_id, tid)
            return create_response(transactions)
        except (LoginError, AgentError) as e:
            status = e.code
            agent_abort(e)
        except Exception as e:
            status = 520
            unknown_abort(e)
        finally:
            thread_pool_executor.submit(publish.status, scheme_account_id, status, tid)


api.add_resource(Transactions, '/<string:scheme_slug>/transactions', endpoint="api.transactions")


class AccountOverview(Resource):
    """Return both a users balance and latest transaction for a specific agent"""
    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        credentials = decrypt_credentials(request.args['credentials'])
        scheme_account_id = int(request.args['scheme_account_id'])
        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class, credentials, scheme_account_id)

        try:
            account_overview = agent_instance.account_overview()
            publish.balance(account_overview["balance"], scheme_account_id, int(request.args['user_id']), tid)
            publish.transactions(account_overview["transactions"], scheme_account_id, tid)

            return create_response(account_overview)
        except (LoginError, AgentError) as e:
            agent_abort(e)
        except Exception as e:
            unknown_abort(e)


api.add_resource(AccountOverview, '/<string:scheme_slug>/account_overview', endpoint="api.account_overview")


class TestResults(Resource):
    """
    This is used for Apollo to access the results of the agent tests run by a cron
    """
    @crossdomain(origin='*')
    def get(self):
        with open(settings.JUNIT_XML_FILENAME) as xml:
            response = make_response(xml.read(), 200)
        response.headers['Content-Type'] = "text/xml"
        return response

api.add_resource(TestResults, '/test_results', endpoint="api.test_results")


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


def agent_login(agent_class, credentials, scheme_account_id):
    key = retry.get_key(agent_class.__name__, scheme_account_id)
    retry_count = retry.get_count(key)
    agent_instance = agent_class(retry_count, scheme_account_id)
    try:
        agent_instance.attempt_login(credentials)
    except RetryLimitError as e:
        retry.max_out_count(key, agent_instance.retry_limit)
        agent_abort(e)
    except (LoginError, AgentError) as e:
        retry.inc_count(key)
        agent_abort(e)
    except Exception as e:
        unknown_abort(e)

    return agent_instance
