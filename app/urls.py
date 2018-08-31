from flask_restful_swagger import swagger
from flask_restful import Api

from app.resources import AgentsErrorResults, Balance, Register, Transactions, ResolveAgentIssue, \
    AccountOverview, TestResults, AgentQuestions, SingleAgentErrorResult, Healthz
from app.resources_callbacks import JoinCallback

api = swagger.docs(Api(), apiVersion='1', api_spec_url="/api/v1/spec")


api.add_resource(Balance, '/<string:scheme_slug>/balance', endpoint="api.points_balance")
api.add_resource(Transactions, '/<string:scheme_slug>/transactions', endpoint="api.transactions")
api.add_resource(Register, '/<string:scheme_slug>/register', endpoint="api.register")
api.add_resource(AccountOverview, '/<string:scheme_slug>/account_overview', endpoint="api.account_overview")

api.add_resource(TestResults, '/test_results', endpoint="api.test_results")
api.add_resource(AgentsErrorResults, '/agents_error_results', endpoint='api.agents_error_results')
api.add_resource(SingleAgentErrorResult, '/agents_error_results/<agent>', endpoint='api.single_agent_error_result')
api.add_resource(ResolveAgentIssue, '/resolve_issue/<string:classname>', endpoint='api.resolve_issue')
api.add_resource(AgentQuestions, '/agent_questions', endpoint='api.agent_questions')

api.add_resource(JoinCallback, '/join/merchant/<string:scheme_slug>', endpoint="api.join_callback")

api.add_resource(Healthz, '/healthz', endpoint='healthz')
