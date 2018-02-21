import functools
import json

from flask import make_response, request
from flask.ext.restful.utils.cors import crossdomain
from flask_restful import Resource, Api, abort
from flask_restful_swagger import swagger
from influxdb.exceptions import InfluxDBClientError
from werkzeug.exceptions import NotFound

import settings
from app import publish
from app import retry
from app.agents.exceptions import (LoginError, AgentError, errors, RetryLimitError, SYSTEM_ACTION_REQUIRED,
                                   ACCOUNT_ALREADY_EXISTS)
from app.encoding import JsonEncoder
from app.encryption import AESCipher
from app.exceptions import AgentException, UnknownException
from app.publish import thread_pool_executor
from app.utils import resolve_agent
from cron_test_results import resolve_issue, get_formatted_message, run_agent_tests, test_single_agent, get_agent_list

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
        scheme_account_id = int(request.args['scheme_account_id'])
        tid = request.headers.get('transaction')

        try:
            agent_class = get_agent_class(scheme_slug)
        except NotFound as e:
            # Update the scheme status on hermes to WALLET_ONLY (10)
            thread_pool_executor.submit(publish.status, scheme_account_id, 10, tid)
            abort(e.code, message=e.data['message'])

        user_id = int(request.args['user_id'])
        credentials = decrypt_credentials(request.args['credentials'])
        agent_instance = agent_login(agent_class, credentials, scheme_account_id, scheme_slug=scheme_slug)

        # Send identifier (e.g membership id) to hermes if it's not already stored.
        if agent_instance.identifier:
            agent_instance.update_scheme_account(scheme_account_id,
                                                 "success",
                                                 tid,
                                                 identifier=agent_instance.identifier)

        try:
            status = 1
            balance = publish.balance(agent_instance.balance(), scheme_account_id,  user_id, tid)
            # Asynchronously get the transactions for the a user
            thread_pool_executor.submit(publish_transactions, agent_instance, scheme_account_id, user_id, tid)

            return create_response(balance)
        except (LoginError, AgentError) as e:
            status = e.code
            raise AgentException(e)
        except Exception as e:
            status = 520

            raise UnknownException(e)
        finally:
            thread_pool_executor.submit(publish.status, scheme_account_id, status, tid)


api.add_resource(Balance, '/<string:scheme_slug>/balance', endpoint="api.points_balance")


def publish_transactions(agent_instance, scheme_account_id, user_id, tid):
    transactions = agent_instance.transactions()
    publish.transactions(transactions, scheme_account_id, user_id, tid)


class Register(Resource):

    def post(self, scheme_slug):
        scheme_account_id = int(request.get_json()['scheme_account_id'])
        tid = request.headers.get('transaction')
        user_id = int(request.get_json()['user_id'])
        credentials = decrypt_credentials(request.get_json()['credentials'])

        thread_pool_executor.submit(registration, scheme_slug, scheme_account_id, credentials, user_id, tid)

        return create_response({"message": "success"})


api.add_resource(Register, '/<string:scheme_slug>/register', endpoint="api.register")


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
        user_id = int(request.args['user_id'])
        credentials = decrypt_credentials(request.args['credentials'])
        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class, credentials, scheme_account_id, scheme_slug=scheme_slug)

        try:
            status = 1
            transactions = publish.transactions(agent_instance.transactions(), scheme_account_id, user_id, tid)
            return create_response(transactions)
        except (LoginError, AgentError) as e:
            status = e.code
            raise AgentException(e)
        except Exception as e:
            status = 520
            raise UnknownException(e)
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
        user_id = int(request.args['user_id'])
        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class, credentials, scheme_account_id, scheme_slug=scheme_slug)

        try:
            account_overview = agent_instance.account_overview()
            publish.balance(account_overview["balance"], scheme_account_id, user_id, tid)
            publish.transactions(account_overview["transactions"], scheme_account_id, user_id, tid)

            return create_response(account_overview)
        except (LoginError, AgentError) as e:
            raise AgentException(e)
        except Exception as e:
            raise UnknownException(e)


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


class ResolveAgentIssue(Resource):
    """
    Called by clicking a 'resolve' link in slack.
    """

    def get(self, classname):
        try:
            resolve_issue(classname)
        except InfluxDBClientError:
            pass
        return 'The specified issue has been resolved.'


api.add_resource(ResolveAgentIssue, '/resolve_issue/<string:classname>', endpoint='api.resolve_issue')


class AgentQuestions(Resource):

    def post(self):
        scheme_slug = request.form['scheme_slug']

        questions = {}
        for k, v in request.form.items():
            if k != 'scheme_slug':
                questions[k] = v

        agent = get_agent_class(scheme_slug)(1, 1, scheme_slug)
        return agent.update_questions(questions)


api.add_resource(AgentQuestions, '/agent_questions', endpoint='api.agent_questions')


class AgentsErrorResults(Resource):

    def get(self):
        # run_agent_tests()
        error_msg = get_formatted_message(settings.JUNIT_XML_FILENAME)
        agent_list = get_agent_list()
        return dict(agents=agent_list, errors=error_msg)


api.add_resource(AgentsErrorResults, '/agents_error_results', endpoint='api.agents_error_results')


class SingleAgentErrorResult(Resource):
    @staticmethod
    def get(agent):
        path = test_single_agent(agent)
        return get_formatted_message(path)


api.add_resource(SingleAgentErrorResult, '/agents_error_results/<agent>', endpoint='api.single_agent_error_result')


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


def agent_login(agent_class, credentials, scheme_account_id, scheme_slug=None, from_register=False):
    key = retry.get_key(agent_class.__name__, scheme_account_id)
    retry_count = retry.get_count(key)
    agent_instance = agent_class(retry_count, scheme_account_id, scheme_slug=scheme_slug)
    try:
        agent_instance.attempt_login(credentials)
    except RetryLimitError as e:
        retry.max_out_count(key, agent_instance.retry_limit)
        raise AgentException(e)
    except (LoginError, AgentError) as e:
        if e.args[0] in SYSTEM_ACTION_REQUIRED and from_register:
            raise e
        retry.inc_count(key)
        raise AgentException(e)
    except Exception as e:
        raise UnknownException(e)

    return agent_instance


def agent_register(agent_class, credentials, scheme_account_id, tid, scheme_slug=None):
    agent_instance = agent_class(0, scheme_account_id, scheme_slug=scheme_slug)
    error = None
    try:
        agent_instance.attempt_register(credentials)
    except Exception as e:
        if not e.args[0] == ACCOUNT_ALREADY_EXISTS:
            agent_instance.update_scheme_account(scheme_account_id, e.args[0], tid)
        else:
            error = ACCOUNT_ALREADY_EXISTS

    return {
        'instance': agent_instance,
        'error': error,
    }


def registration(scheme_slug, scheme_account_id, credentials, user_id, tid):
    try:
        agent_class = get_agent_class(scheme_slug)
    except NotFound as e:
        # Update the scheme status on hermes to JOIN(900)
        publish.status(scheme_account_id, 900, tid)
        abort(e.code, message=e.data['message'])

    register_result = agent_register(agent_class, credentials, scheme_account_id, tid, scheme_slug=scheme_slug)

    try:
        agent_instance = agent_login(agent_class, credentials, scheme_account_id, scheme_slug=scheme_slug,
                                     from_register=True)
        agent_instance.update_scheme_account(scheme_account_id, "success", tid, identifier=agent_instance.identifier)
    except (LoginError, AgentError, AgentException) as e:
        if register_result['error'] == ACCOUNT_ALREADY_EXISTS:
            register_result['instance'].update_scheme_account(scheme_account_id, str(e.args[0]), tid)
        else:
            publish.zero_balance(scheme_account_id, user_id, tid)
        return True

    try:
        status = 1
        publish.balance(agent_instance.balance(), scheme_account_id, user_id, tid)
        publish_transactions(agent_instance, scheme_account_id, user_id, tid)
    except Exception as e:
        status = 520
        raise UnknownException(e)
    finally:
        publish.status(scheme_account_id, status, tid)
        return True
