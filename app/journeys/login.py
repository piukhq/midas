from app.agents.schemas import balance_tuple_to_dict, transaction_tuple_to_dict
from app.journeys.common import agent_login
from app.reporting import get_logger
from app.scheme_account import update_pending_join_account

log = get_logger("login-journey")


def login(agent_instance, user_info, transaction_id):
    agent_instance.attempt_login(user_info["credentials"])

    # Update Hermes with agent identifier
    if agent_instance.identifier:
        update_pending_join_account(user_info, "success", transaction_id, identifier=agent_instance.identifier)

    # Get balance
    balance = balance_tuple_to_dict(agent_instance.balance())

    # Get transactions
    transactions = agent_instance.transactions()
    transactions = [transaction_tuple_to_dict(tx) for tx in transactions]

    # Harvey Nicols appears to be the only agent that requires this
    # WHY is it necessary?
    create_journey = agent_instance.create_journey

    return balance, transactions, create_journey
