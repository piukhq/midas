import json
from uuid import uuid4

import olympus_messaging
import requests
from flask import make_response, request
from flask_restful import Resource, abort
from flask_restful.utils.cors import crossdomain
from werkzeug.exceptions import NotFound

import settings
from app import publish
from app.agents.schemas import transaction_tuple_to_dict
from app.encoding import JsonEncoder
from app.encryption import AESCipher, get_aes_key
from app.exceptions import BaseError, UnknownError
from app.journeys.common import agent_login, get_agent_class
from app.journeys.view import async_get_balance_and_publish, get_balance_and_publish
from app.messaging import queue
from app.publish import thread_pool_executor
from app.reporting import get_logger
from app.scheme_account import SchemeAccountStatus

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
        bink_user_id = request.args.get("bink_user_id", type=int)
        status = request.args.get("status")
        journey_type = request.args.get("journey_type")
        user_set = get_user_set_from_request(request.args)
        if not user_set:
            abort(400, message='Please provide either "user_set" or "user_id" parameters')

        user_info = {
            "credentials": decrypt_credentials(request.args["credentials"]),
            "status": int(status) if status else None,
            "user_set": user_set,
            "bink_user_id": bink_user_id,
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
        # Return the bink_user_id back to hermes. When messaging implemented, this will need reviewing.
        if balance:
            balance["bink_user_id"] = bink_user_id
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
        # Adding the bink_user_id here for completeness, we do not have any async agents, so not used.
        # Messaging work will probably remove the requirement for this function.
        if prev_balance:
            prev_balance["bink_user_id"] = user_info["bink_user_id"]
        # return previous balance from hades so front end has something to display
        return prev_balance


class Join(Resource):
    def post(self, scheme_slug):
        data = request.get_json()
        scheme_account_id = str(data["scheme_account_id"])

        log.debug(f"Creating join task for scheme account: {scheme_account_id}")

        user_id = str(data["user_id"])

        message = olympus_messaging.JoinApplication(
            channel=data["channel"],
            transaction_id=request.headers.get("X-Azure-Ref", uuid4().hex),
            bink_user_id=user_id,
            request_id=scheme_account_id,
            loyalty_plan=scheme_slug,
            account_id=scheme_account_id,
            join_data={"encrypted_credentials": data["credentials"]},
        )

        queue.enqueue_request(message)

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
                [transaction_tuple_to_dict(tx) for tx in agent_instance.transactions()],
                user_info["scheme_account_id"],
                user_info["user_set"],
                tid,
            )
            return create_response(transactions)
        except BaseError as e:
            status = e.code
            raise e
        except Exception as e:
            status = SchemeAccountStatus.UNKNOWN_ERROR
            raise UnknownError(exception=e) from e
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
        except Exception as e:
            raise UnknownError(exception=e) from e


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
    aes = AESCipher(get_aes_key("aes-keys"))
    return json.loads(aes.decrypt(credentials.replace(" ", "+")))


def create_response(response_data):
    response = make_response(json.dumps(response_data, cls=JsonEncoder), 200)
    response.headers["Content-Type"] = "application/json"
    return response


def get_hades_balance(scheme_account_id):
    resp = requests.get(
        settings.HADES_URL + "/balances/scheme_account/" + str(scheme_account_id),
        headers={"Authorization": "Token " + settings.SERVICE_API_KEY},
    )

    try:
        resp_json = resp.json()
    except (AttributeError, TypeError) as e:
        raise UnknownError(exception=e) from e
    else:
        if resp_json:
            return resp_json
        raise UnknownError(message="Empty response getting previous balance")


def get_user_set_from_request(request_args):
    try:
        return request_args.get("user_set") or str(request_args["user_id"])
    except KeyError:
        return None
