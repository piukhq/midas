from app.scheme_account import JourneyTypes, SchemeAccountStatus

AGENT_CLASS_ARGUMENTS = (
    1,
    {
        "scheme_account_id": 1,
        "status": SchemeAccountStatus.ACTIVE,
        "user_set": "1,2",
        "journey_type": None,
        "credentials": {},
        "channel": "com.bink.wallet",
    },
)

AGENT_CLASS_ARGUMENTS_FOR_VALIDATE = (
    1,
    {
        "scheme_account_id": 1,
        "status": SchemeAccountStatus.WALLET_ONLY,
        "journey_type": JourneyTypes.LINK.value,
        "user_set": "1,2",
    },
)
