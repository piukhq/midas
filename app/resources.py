import importlib
import json
import traceback

import requests
import sentry_sdk
from flask import make_response, request
from flask_restful import Resource, abort
from flask_restful.utils.cors import crossdomain
from werkzeug.exceptions import NotFound
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

import settings
from app import publish, retry
from app.active import AGENTS
from app.agents.base import MerchantApi
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    SCHEME_REQUESTED_DELETE,
    SYSTEM_ACTION_REQUIRED,
    UNKNOWN,
    AgentError,
    LoginError,
    RetryLimitError,
    errors,
)
from app.encoding import JsonEncoder
from app.encryption import AESCipher
from app.exceptions import AgentException, UnknownException
from app.http_request import get_headers
from app.publish import PENDING_BALANCE, create_balance_object, thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import (
    JourneyTypes,
    SchemeAccountStatus,
    delete_scheme_account,
    update_pending_join_account,
    update_pending_link_account,
)

scheme_account_id_doc = {
    "name": "scheme_account_id",
    "required": True,
    "dataType": "integer",
    "paramType": "query",
}
user_id_doc = {
    "name": "user_id",
    "required": False,
    "dataType": "integer",
    "paramType": "query",
}
user_set_doc = {
    "name": "user_set",
    "required": False,
    "dataType": "string",
    "paramType": "query",
}
credentials_doc = {
    "name": "credentials",
    "required": True,
    "dataType": "string",
    "paramType": "query",
}


log = get_logger("api")


class Healthz(Resource):
    def get(self):
        return ""


class Balance(Resource):
    def get(self, scheme_slug):
        status = request.args.get("status")
        journey_type = request.args.get("journey_type")
        user_set = get_user_set_from_request(request.args)
        if not user_set:
            abort(400, message='Please provide either "user_set" or "user_id" parameters')

        user_info = {
            "credentials": decrypt_credentials(request.args["credentials"]),
            "status": int(status) if status else None,
            "user_set": user_set,
            "journey_type": int(journey_type) if journey_type else None,
            "scheme_account_id": int(request.args["scheme_account_id"]),
        }
        tid = request.headers.get("transaction")

        try:
            agent_class = get_agent_class(scheme_slug)
        except NotFound as e:
            # Update the scheme status on hermes to WALLET_ONLY (10)
            thread_pool_executor.submit(publish.status, user_info["scheme_account_id"], 10, tid, user_info)
            abort(e.code, message=e.data["message"])

        if agent_class.is_async:
            return create_response(self.handle_async_balance(agent_class, scheme_slug, user_info, tid))

        balance = get_balance_and_publish(agent_class, scheme_slug, user_info, tid)
        return create_response(balance)

    @staticmethod
    def handle_async_balance(agent_class, scheme_slug, user_info, tid):
        scheme_account_id = user_info["scheme_account_id"]
        if user_info["status"] == SchemeAccountStatus.WALLET_ONLY:
            prev_balance = publish.zero_balance(scheme_account_id, tid, user_info["user_set"])
            publish.status(scheme_account_id, 0, tid, user_info)
        else:
            prev_balance = get_hades_balance(scheme_account_id)

        user_info["pending"] = False
        if user_info["status"] in [
            SchemeAccountStatus.PENDING,
            SchemeAccountStatus.WALLET_ONLY,
        ]:
            user_info["pending"] = True
            prev_balance["pending"] = True

        thread_pool_executor.submit(async_get_balance_and_publish, agent_class, scheme_slug, user_info, tid)
        # return previous balance from hades so front end has something to display
        return prev_balance


def get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info["scheme_account_id"]
    threads = []
    create_journey = None

    status = SchemeAccountStatus.UNKNOWN_ERROR
    try:
        balance, status, create_journey = request_balance(
            agent_class, user_info, scheme_account_id, scheme_slug, tid, threads
        )
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
        if user_info.get("pending") and not status == SchemeAccountStatus.ACTIVE:
            pass
        elif status is None:
            pass
        else:
            threads.append(
                thread_pool_executor.submit(
                    publish.status,
                    scheme_account_id,
                    status,
                    tid,
                    user_info,
                    journey=create_journey,
                )
            )

        [thread.result() for thread in threads]
        if status == errors[SCHEME_REQUESTED_DELETE]["code"]:
            log.debug(
                f"Received deleted request from scheme: {scheme_slug}. Deleting scheme account: {scheme_account_id}"
            )
            delete_scheme_account(tid, scheme_account_id)


def request_balance(agent_class, user_info, scheme_account_id, scheme_slug, tid, threads):
    create_journey = None
    # Pending scheme account using the merchant api framework expects a callback so should not call balance unless
    # the call is an async Link.
    is_merchant_api_agent = issubclass(agent_class, MerchantApi)
    check_status = user_info["status"]
    is_pending = check_status in [
        SchemeAccountStatus.PENDING,
        SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
    ]
    if is_merchant_api_agent and is_pending and user_info["journey_type"] != JourneyTypes.LINK:
        user_info["pending"] = True
        status = check_status
        balance = create_balance_object(PENDING_BALANCE, scheme_account_id, user_info["user_set"])
    else:
        if scheme_slug == "iceland-bonus-card" and settings.ENABLE_ICELAND_VALIDATE:
            if user_info["status"] != SchemeAccountStatus.ACTIVE:
                user_info["journey_type"] = JourneyTypes.LINK.value

        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug)

        # Send identifier (e.g membership id) to hermes if it's not already stored.
        if agent_instance.identifier:
            update_pending_join_account(user_info, "success", tid, identifier=agent_instance.identifier)

        balance_result = agent_instance.balance()
        if not balance_result:
            return None, None, None

        balance = publish.balance(balance_result._asdict(), scheme_account_id, user_info["user_set"], tid)

        # Asynchronously get the transactions for the a user
        threads.append(
            thread_pool_executor.submit(
                publish_transactions,
                agent_instance,
                scheme_account_id,
                user_info["user_set"],
                tid,
            )
        )
        status = SchemeAccountStatus.ACTIVE
        create_journey = agent_instance.create_journey

    return balance, status, create_journey


def async_get_balance_and_publish(agent_class, scheme_slug, user_info, tid):
    scheme_account_id = user_info["scheme_account_id"]
    try:
        balance = get_balance_and_publish(agent_class, scheme_slug, user_info, tid)
        return balance

    except (AgentException, UnknownException) as e:
        if user_info.get("pending"):
            message = f"Error with async linking. Scheme: {scheme_slug}, Error: {repr(e)}"
            update_pending_link_account(user_info, message, tid, scheme_slug=scheme_slug)
        else:
            status = e.status_code
            requests.post(
                f"{settings.HERMES_URL}/schemes/accounts/{scheme_account_id}/status",
                data=json.dumps({"status": status, "user_info": user_info}, cls=JsonEncoder),
                headers=get_headers(tid),
            )

        raise e


def publish_transactions(agent_instance, scheme_account_id, user_set, tid):
    transactions = agent_instance.transactions()
    publish.transactions([tx._asdict() for tx in transactions], scheme_account_id, user_set, tid)


class Register(Resource):
    def post(self, scheme_slug):
        data = request.get_json()
        scheme_account_id = int(data["scheme_account_id"])
        user_info = {
            "user_set": get_user_set_from_request(data),
            "credentials": decrypt_credentials(request.get_json()["credentials"]),
            "status": int(data["status"]),
            "journey_type": int(data["journey_type"]),
            "scheme_account_id": scheme_account_id,
            "channel": data.get("channel", ""),
        }
        tid = request.headers.get("transaction")

        log.debug("Creating registration task for scheme account: {scheme_account_id}")
        thread_pool_executor.submit(registration, scheme_slug, user_info, tid)

        return create_response({"message": "success"})


class Transactions(Resource):
    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        user_set = get_user_set_from_request(request.args)
        if not user_set:
            abort(400, message='Please provide either "user_set" or "user_id" parameters')

        user_info = {
            "user_set": user_set,
            "credentials": decrypt_credentials(request.args["credentials"]),
            "status": request.args.get("status"),
            "scheme_account_id": int(request.args["scheme_account_id"]),
        }

        tid = request.headers.get("transaction")
        status = SchemeAccountStatus.ACTIVE

        try:
            agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug)

            transactions = publish.transactions(
                [tx._asdict() for tx in agent_instance.transactions()],
                user_info["scheme_account_id"],
                user_info["user_set"],
                tid,
            )
            return create_response(transactions)
        except (LoginError, AgentError) as e:
            status = e.code
            raise AgentException(e)
        except Exception as e:
            status = SchemeAccountStatus.UNKNOWN_ERROR
            raise UnknownException(e)
        finally:
            thread_pool_executor.submit(publish.status, user_info["scheme_account_id"], status, tid, user_info)


class AccountOverview(Resource):
    """Return both a users balance and latest transaction for a specific agent"""

    def get(self, scheme_slug):
        agent_class = get_agent_class(scheme_slug)
        user_set = get_user_set_from_request(request.args)
        user_info = {
            "user_set": user_set,
            "credentials": decrypt_credentials(request.args["credentials"]),
            "status": request.args.get("status"),
            "scheme_account_id": int(request.args["scheme_account_id"]),
        }

        tid = request.headers.get("transaction")
        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug)
        try:
            account_overview = agent_instance.account_overview()
            publish.balance(
                account_overview["balance"],
                user_info["scheme_account_id"],
                user_info["user_set"],
                tid,
            )
            publish.transactions(
                account_overview["transactions"],
                user_info["scheme_account_id"],
                user_info["user_set"],
                tid,
            )

            return create_response(account_overview)
        except (LoginError, AgentError) as e:
            raise AgentException(e)
        except Exception as e:
            raise UnknownException(e)


class TestResults(Resource):
    """
    This is used for Apollo to access the results of the agent tests run by a cron
    """

    @crossdomain(origin="*")
    def get(self):
        with open(settings.JUNIT_XML_FILENAME) as xml:
            response = make_response(xml.read(), 200)
        response.headers["Content-Type"] = "text/xml"
        return response


class AgentQuestions(Resource):
    def post(self):
        scheme_slug = request.form["scheme_slug"]

        questions = {}
        for k, v in request.form.items():
            if k != "scheme_slug":
                questions[k] = v

        agent = get_agent_class(scheme_slug)(1, {"scheme_account_id": 1, "status": 1}, scheme_slug)
        return agent.update_questions(questions)


def decrypt_credentials(credentials):
    hermes_aes_keys = get_vault_aes_key()
    aes_key = json.loads(hermes_aes_keys)["AES_KEY"]
    aes = AESCipher(aes_key.encode())
    return json.loads(aes.decrypt(credentials.replace(" ", "+")))


def get_vault_aes_key():
    client = SecretClient(
        vault_url=settings.VAULT_URL,
        credential=DefaultAzureCredential()
    )
    return client.get_secret("aes-keys").value


def create_response(response_data):
    response = make_response(json.dumps(response_data, cls=JsonEncoder), 200)
    response.headers["Content-Type"] = "application/json"
    return response


def get_agent_class(scheme_slug):
    try:
        return resolve_agent(scheme_slug)
    except KeyError:
        performance_slugs = ["performance-mock", "performance-voucher-mock"]
        for performance_slug in performance_slugs:
            if scheme_slug.startswith(performance_slug):
                return resolve_agent(performance_slug)

        abort(404, message="No such agent")


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
    key = retry.get_key(agent_class.__name__, user_info["scheme_account_id"])
    retry_count = retry.get_count(key)
    if from_register:
        user_info["journey_type"] = JourneyTypes.UPDATE.value
        user_info["from_register"] = True

    agent_instance = agent_class(retry_count, user_info, scheme_slug=scheme_slug)
    try:
        agent_instance.attempt_login(user_info["credentials"])
    except RetryLimitError as e:
        retry.max_out_count(key, agent_instance.retry_limit)
        raise AgentException(e)
    except (LoginError, AgentError) as e:
        # If this is an UNKNOWN error, also log to sentry
        if e.code == errors[UNKNOWN]["code"]:
            sentry_sdk.capture_exception()
        if e.args[0] in SYSTEM_ACTION_REQUIRED and from_register:
            raise e
        retry.inc_count(key)
        raise AgentException(e)
    except Exception as e:
        raise UnknownException(e) from e

    return agent_instance


def agent_register(agent_class, user_info, tid, scheme_slug=None):
    agent_instance = agent_class(0, user_info, scheme_slug=scheme_slug)
    error = None
    try:
        agent_instance.attempt_register(user_info["credentials"])
    except Exception as e:
        error = e.args[0]

        consents = user_info["credentials"].get("consents", [])
        consent_ids = (consent["id"] for consent in consents)
        update_pending_join_account(user_info, e.args[0], tid, scheme_slug=scheme_slug, consent_ids=consent_ids)

    return {"agent": agent_instance, "error": error}


def log_task(func):
    def logged_func(*args, **kwargs):
        try:
            scheme_account_message = f" for scheme account: {args[1]['scheme_account_id']}"
        except KeyError:
            scheme_account_message = ""

        try:
            log.debug(f"Starting {func.__name__} task{scheme_account_message}")
            result = func(*args, **kwargs)
            log.debug(f"Finished {func.__name__} task{scheme_account_message}")
        except Exception as e:
            # If this is an UNKNOWN error, also log to sentry but first make this a more specific UnknownException
            if isinstance(e, AgentException) and e.status_code == errors[UNKNOWN]["code"]:
                try:
                    raise UnknownException(scheme_account_message) from e
                except UnknownException as ue:
                    sentry_sdk.capture_exception(ue)

            # Extract stack trace from exception
            tb_str = "".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
            log.debug(f"Error with {func.__name__} task{scheme_account_message}. error: {repr(e)}, traceback: {tb_str}")
            raise

        return result

    return logged_func


@log_task
def registration(scheme_slug, user_info, tid):
    try:
        agent_class = get_agent_class(scheme_slug)
    except NotFound as e:
        # Update the scheme status on hermes to JOIN(900)
        publish.status(user_info["scheme_account_id"], 900, tid, user_info)
        abort(e.code, message=e.data["message"])

    register_result = agent_register(agent_class, user_info, tid, scheme_slug=scheme_slug)
    try:
        if register_result["agent"].expecting_callback:
            return True
        agent_instance = agent_login(agent_class, user_info, scheme_slug=scheme_slug, from_register=True)
        if agent_instance.identifier:
            update_pending_join_account(user_info, "success", tid, identifier=agent_instance.identifier)
        elif register_result["agent"].identifier:
            update_pending_join_account(
                user_info,
                "success",
                tid,
                identifier=register_result["agent"].identifier,
            )
    except (LoginError, AgentError, AgentException) as e:
        if register_result["error"] == ACCOUNT_ALREADY_EXISTS:
            consents = user_info["credentials"].get("consents", [])
            consent_ids = (consent["id"] for consent in consents)
            update_pending_join_account(
                user_info,
                str(e.args[0]),
                tid,
                scheme_slug=scheme_slug,
                consent_ids=consent_ids,
            )
        else:
            publish.zero_balance(user_info["scheme_account_id"], user_info["user_set"], tid)
        return True

    status = SchemeAccountStatus.ACTIVE
    try:
        publish.balance(
            agent_instance.balance()._asdict(),
            user_info["scheme_account_id"],
            user_info["user_set"],
            tid,
        )
        publish_transactions(agent_instance, user_info["scheme_account_id"], user_info["user_set"], tid)
    except Exception as e:
        status = SchemeAccountStatus.UNKNOWN_ERROR
        raise UnknownException(e)
    finally:
        publish.status(user_info["scheme_account_id"], status, tid, user_info, journey="join")
        return True


def get_hades_balance(scheme_account_id):
    resp = requests.get(
        settings.HADES_URL + "/balances/scheme_account/" + str(scheme_account_id),
        headers={"Authorization": "Token " + settings.SERVICE_API_KEY},
    )

    try:
        resp_json = resp.json()
    except (AttributeError, TypeError) as e:
        raise UnknownException(e)
    else:
        if resp_json:
            return resp_json
        raise UnknownException("Empty response getting previous balance")


def get_user_set_from_request(request_args):
    try:
        return request_args.get("user_set") or str(request_args["user_id"])
    except KeyError:
        return None


def resolve_agent(name):
    class_path = AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module("app.agents.{}".format(module_name))
    return getattr(module, class_name)
