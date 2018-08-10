import functools
import json
from datetime import datetime

import requests
from flask import make_response, request
from flask.ext.restful.utils.cors import crossdomain
from flask_restful import Resource, abort
from flask_restful_swagger import swagger
from influxdb.exceptions import InfluxDBClientError
from werkzeug.exceptions import NotFound

import settings
from cron_test_results import resolve_issue, get_formatted_message, handle_helios_request, test_single_agent
from settings import HADES_URL, HERMES_URL, SERVICE_API_KEY, logger
from app import retry, publish
from app.encoding import JsonEncoder
from app.encryption import AESCipher
from app.exceptions import AgentException, UnknownException
from app.publish import thread_pool_executor
from app.utils import resolve_agent, raise_intercom_event, get_headers, SchemeAccountStatus, log_task
from app.agents.exceptions import (LoginError, AgentError, errors, RetryLimitError, SYSTEM_ACTION_REQUIRED,
                                   ACCOUNT_ALREADY_EXISTS)

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


class Healthz(Resource):
    def get(self):
        return ''


class Balance(Resource):

    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
        notes="Return a users balance for a specific agent"
    )
    def get(self, scheme_slug):
        status = request.args.get('status')
        journey_type = request.args.get('journey_type')
        user_info = {
            'user_id': int(request.args['user_id']),
            'credentials': decrypt_credentials(request.args['credentials']),
            'status': int(status) if status else None,
            'journey_type': int(journey_type) if journey_type else None,
            'scheme_account_id': int(request.args['scheme_account_id']),
        }
        tid = request.headers.get('transaction')

        try:
            agent_class = get_agent_class(scheme_slug)
        except NotFound as e:
            # Update the scheme status on hermes to WALLET_ONLY (10)
            thread_pool_executor.submit(publish.status, user_info['scheme_account_id'], 10, tid)
            abort(e.code, message=e.data['message'])

        if agent_class.async:
            return create_response(self.handle_async_balance(agent_class, scheme_slug, user_info, tid))

        balance = get_balance_and_publish(agent_class, scheme_slug, user_info, tid)
        return create_response(balance)

    @staticmethod
    def handle_async_balance(agent_class, scheme_slug, user_info, tid):
        scheme_account_id = user_info['scheme_account_id']
        if user_info['status'] == SchemeAccountStatus.WALLET_ONLY:
            prev_balance = publish.zero_balance(scheme_account_id, user_info['user_id'], tid)
            publish.status(scheme_account_id, 0, tid)
        else:
            prev_balance = get_hades_balance(scheme_account_id)

        user_info['pending'] = False
        if user_info['status'] in [SchemeAccountStatus.PENDING, SchemeAccountStatus.WALLET_ONLY]:
            user_info['pending'] = True
            prev_balance['pending'] = True

        thread_pool_executor.submit(async_get_balance_and_publish, agent_class, scheme_slug, user_info, tid)
        # return previous balance from hades so front end has something to display
        return prev_balance


def get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info['scheme_account_id']
    threads = []

    status = SchemeAccountStatus.ACTIVE
    try:
        agent_instance = agent_login(agent_class,
                                     user_info,
                                     scheme_slug=scheme_slug)

        # Send identifier (e.g membership id) to hermes if it's not already stored.
        if agent_instance.identifier:
            update_pending_join_account(scheme_account_id, "success", tid, identifier=agent_instance.identifier)

        balance = publish.balance(agent_instance.balance(), scheme_account_id,  user_info['user_id'], tid)
        # Asynchronously get the transactions for the a user
        threads.append(thread_pool_executor.submit(publish_transactions, agent_instance, scheme_account_id,
                                                   user_info['user_id'], tid))
        return balance
    except (LoginError, AgentError) as e:
        status = e.code
        raise AgentException(e)
    except AgentException as e:
        status = e.status_code
        raise
    except Exception as e:
        status = SchemeAccountStatus.UNKNOWN_ERROR
        raise UnknownException(e)
    finally:
        if user_info.get('pending') and not status == SchemeAccountStatus.ACTIVE:
            pass
        else:
            threads.append(thread_pool_executor.submit(publish.status, scheme_account_id, status, tid))

        [thread.result() for thread in threads]


def async_get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info['scheme_account_id']
    try:
        balance = get_balance_and_publish(agent_class, scheme_slug, user_info, tid)
        return balance

    except (AgentException, UnknownException) as e:
        if user_info.get('pending'):
            intercom_data = {
                'user_id': user_info['user_id'],
                'metadata': {'scheme': scheme_slug},
            }
            message = 'Error with async linking. Scheme: {}, Error: {}'.format(scheme_slug, str(e))
            update_pending_link_account(scheme_account_id, message, tid, intercom_data=intercom_data)
        else:
            status = e.status_code
            requests.post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id),
                          data=json.dumps({'status': status}, cls=JsonEncoder), headers=get_headers(tid))

        raise e


def publish_transactions(agent_instance, scheme_account_id, user_id, tid):
    transactions = agent_instance.transactions()
    publish.transactions(transactions, scheme_account_id, user_id, tid)


class Register(Resource):

    def post(self, scheme_slug):
        data = request.get_json()
        scheme_account_id = int(data['scheme_account_id'])
        journey_type = data['journey_type']
        status = int(data['status'])
        user_info = {
            'user_id': int(request.get_json()['user_id']),
            'credentials': decrypt_credentials(request.get_json()['credentials']),
            'status': status,
            'journey_type': int(journey_type),
            'scheme_account_id': scheme_account_id,
        }
        tid = request.headers.get('transaction')

        logger.debug(
            "{0} - creating registration task for scheme account: {1}".format(datetime.now(), scheme_account_id)
        )
        thread_pool_executor.submit(registration, scheme_slug, user_info, tid)

        return create_response({"message": "success"})


class Transactions(Resource):

    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        notes="Return a users latest transactions for a specific agent",
        parameters=[scheme_account_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)

        user_info = {
            'user_id': int(request.args['user_id']),
            'credentials': decrypt_credentials(request.args['credentials']),
            'status': request.args.get('status'),
            'scheme_account_id': int(request.args['scheme_account_id']),
        }

        tid = request.headers.get('transaction')
        status = SchemeAccountStatus.ACTIVE

        try:
            agent_instance = agent_login(agent_class,
                                         user_info,
                                         scheme_slug=scheme_slug)

            transactions = publish.transactions(agent_instance.transactions(),
                                                user_info['scheme_account_id'],
                                                user_info['user_id'],
                                                tid)
            return create_response(transactions)
        except (LoginError, AgentError) as e:
            status = e.code
            raise AgentException(e)
        except Exception as e:
            status = SchemeAccountStatus.UNKNOWN_ERROR
            raise UnknownException(e)
        finally:
            thread_pool_executor.submit(publish.status, user_info['scheme_account_id'], status, tid)


class AccountOverview(Resource):
    """Return both a users balance and latest transaction for a specific agent"""
    @validate_parameters
    @swagger.operation(
        responseMessages=list(errors.values()),
        parameters=[scheme_account_id_doc, user_id_doc, credentials_doc],
    )
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        user_info = {
            'user_id': int(request.args['user_id']),
            'credentials': decrypt_credentials(request.args['credentials']),
            'status': request.args.get('status'),
            'scheme_account_id': int(request.args['scheme_account_id']),
        }

        tid = request.headers.get('transaction')
        agent_instance = agent_login(agent_class,
                                     user_info,
                                     scheme_slug=scheme_slug)
        try:
            account_overview = agent_instance.account_overview()
            publish.balance(account_overview["balance"],
                            user_info['scheme_account_id'],
                            user_info['user_id'],
                            tid)
            publish.transactions(account_overview["transactions"],
                                 user_info['scheme_account_id'],
                                 user_info['user_id'],
                                 tid)

            return create_response(account_overview)
        except (LoginError, AgentError) as e:
            raise AgentException(e)
        except Exception as e:
            raise UnknownException(e)


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


class AgentQuestions(Resource):

    def post(self):
        scheme_slug = request.form['scheme_slug']

        questions = {}
        for k, v in request.form.items():
            if k != 'scheme_slug':
                questions[k] = v

        agent = get_agent_class(scheme_slug)(1, {'scheme_account_id': 1, 'status': 1}, scheme_slug)
        return agent.update_questions(questions)


class AgentsErrorResults(Resource):
    @staticmethod
    def get():
        thread_pool_executor.submit(handle_helios_request)
        return dict(success=True, errors=None)


class SingleAgentErrorResult(Resource):
    @staticmethod
    def get(agent):
        path = test_single_agent(agent)
        return get_formatted_message(path)


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


def agent_login(agent_class, user_info, scheme_slug=None, from_register=False):
    """
    Instantiates an agent class and attempts to login.
    :param agent_class: Class object inheriting BaseMiner class.
    :param user_info: Dictionary of user information.
    {
        'user_id': int,
        'credentials': str,
        'status': str,
        'scheme_account_id': int
        'journey_type': int
    }
    :param scheme_slug: String of merchant identifier e.g 'harvey-nichols'
    :param from_register: Boolean of whether the login call is from the registration process.
    :return: Class instance of the agent.
    """
    key = retry.get_key(agent_class.__name__, user_info['scheme_account_id'])
    retry_count = retry.get_count(key)
    agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)
    try:
        agent_instance.attempt_login(user_info['credentials'])
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


def agent_register(agent_class, user_info, intercom_data, tid, scheme_slug=None):
    agent_instance = agent_class(0, user_info, scheme_slug=scheme_slug)
    error = None
    try:
        agent_instance.attempt_register(user_info['credentials'])
    except Exception as e:
        if not e.args[0] == ACCOUNT_ALREADY_EXISTS:
            update_pending_join_account(user_info['scheme_account_id'], e.args[0], tid, intercom_data=intercom_data)
        else:
            error = ACCOUNT_ALREADY_EXISTS

    return {
        'error': error,
    }


@log_task
def registration(scheme_slug, user_info, tid):
    intercom_data = {
        'user_id': user_info['user_id'],
        'metadata': {'scheme': scheme_slug},
    }

    try:
        agent_class = get_agent_class(scheme_slug)
    except NotFound as e:
        # Update the scheme status on hermes to JOIN(900)
        publish.status(user_info['scheme_account_id'], 900, tid)
        abort(e.code, message=e.data['message'])

    register_result = agent_register(agent_class, user_info, intercom_data, tid,
                                     scheme_slug=scheme_slug)
    try:
        if agent_class.expecting_callback:
            return True
        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug,
                                     from_register=True)
        if agent_instance.identifier:
            update_pending_join_account(user_info['scheme_account_id'], "success", tid,
                                        identifier=agent_instance.identifier)
    except (LoginError, AgentError, AgentException) as e:
        if register_result['error'] == ACCOUNT_ALREADY_EXISTS:
            update_pending_join_account(user_info['scheme_account_id'], str(e.args[0]), tid,
                                        intercom_data=intercom_data)
        else:
            publish.zero_balance(user_info['scheme_account_id'], user_info['user_id'], tid)
        return True

    try:
        status = SchemeAccountStatus.ACTIVE
        publish.balance(agent_instance.balance(), user_info['scheme_account_id'], user_info['user_id'], tid)
        publish_transactions(agent_instance, user_info['scheme_account_id'], user_info['user_id'], tid)
    except Exception as e:
        status = SchemeAccountStatus.UNKNOWN_ERROR
        raise UnknownException(e)
    finally:
        publish.status(user_info['scheme_account_id'], status, tid)
        return True


def get_hades_balance(scheme_account_id):
    resp = requests.get(HADES_URL + '/balances/scheme_account/' + str(scheme_account_id),
                        headers={'Authorization': 'Token ' + SERVICE_API_KEY})

    if resp:
        return resp.json()

    return resp


def update_pending_join_account(scheme_account_id, message, tid, identifier=None, intercom_data=None):
    # for updating user ID credential you get for registering (e.g. getting issued a card number)
    if identifier:
        requests.put('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                     data=json.dumps(identifier, cls=JsonEncoder), headers=get_headers(tid))
        return

    # error handling for pending scheme accounts waiting for join journey to complete
    data = {'status': SchemeAccountStatus.JOIN}
    requests.post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id),
                  data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid))

    data = {'all': True}
    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(data, cls=JsonEncoder), headers=get_headers(tid))

    metadata = intercom_data['metadata']
    raise_intercom_event('join-failed-event', intercom_data['user_id'], metadata)

    raise AgentException(message)


def update_pending_link_account(scheme_account_id, message, tid, intercom_data=None):
    # error handling for pending scheme accounts waiting for async link to complete
    status_data = {'status': SchemeAccountStatus.WALLET_ONLY}
    requests.post("{}/schemes/accounts/{}/status".format(HERMES_URL, scheme_account_id),
                  data=json.dumps(status_data, cls=JsonEncoder), headers=get_headers(tid))

    question_data = {'property_list': ['link_questions']}
    requests.delete('{}/schemes/accounts/{}/credentials'.format(HERMES_URL, scheme_account_id),
                    data=json.dumps(question_data), headers=get_headers(tid))

    metadata = intercom_data['metadata']
    raise_intercom_event('async-link-failed-event', intercom_data['user_id'], metadata)

    raise AgentException(message)
