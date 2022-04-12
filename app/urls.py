from flask_restful import Api

from app.bpl_callback import JoinCallbackBpl
from app.resources import AccountOverview, AgentQuestions, Healthz, Join, Login, Transactions
from app.resources_callbacks import JoinCallback

api = Api()

api.add_resource(Login, "/<string:scheme_slug>/balance", endpoint="api.points_balance")
api.add_resource(Transactions, "/<string:scheme_slug>/transactions", endpoint="api.transactions")
api.add_resource(Join, "/<string:scheme_slug>/register", endpoint="api.register")
api.add_resource(Join, "/<string:scheme_slug>/join", endpoint="api.join")
api.add_resource(AccountOverview, "/<string:scheme_slug>/account_overview", endpoint="api.account_overview")

api.add_resource(AgentQuestions, "/agent_questions", endpoint="api.agent_questions")

api.add_resource(JoinCallback, "/join/merchant/<string:scheme_slug>", endpoint="api.join_callback")
api.add_resource(JoinCallbackBpl, "/join/bpl/<string:scheme_slug>", endpoint="api.join_callback_bpl")

api.add_resource(Healthz, "/healthz", endpoint="healthz")
