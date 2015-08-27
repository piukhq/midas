# based on https://developer.yodlee.com/FAQs/Error_Codes

errors = {
    "STATUS_LOGIN_FAILED": {"code": 402,
                            "message": "We could not update your account because your username and/or password were"
                                       "reported to be incorrect. Please re-verify your username and password."},
    "INVALID_MFA_INFO": {"code": 234,
                         "message": "We're sorry, the authentication information you  provided is incorrect. "
                                    "Please try again."},
    "AGENT_DOWN": {"code": 235,
                   "message": "The agent is currently down for maintenance."},
    "UNKNOWN": {"code": 666,
                "message": "We have know the idea what went wrong the team is on to it."}

}


class MinerError(Exception):
    """Exception raised for errors in the input.
    """
    def __init__(self, name):
        self.name = name
        self.message = errors[name]['message']
        self.code = errors[name]['code']


