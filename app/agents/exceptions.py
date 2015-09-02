# based on https://developer.yodlee.com/FAQs/Error_Codes

STATUS_ACCOUNT_LOCKED = "STATUS_ACCOUNT_LOCKED"
STATUS_LOGIN_FAILED = "STATUS_LOGIN_FAILED"
INVALID_MFA_INFO = "INVALID_MFA_INFO"
AGENT_DOWN = "AGENT_DOWN"
UNKNOWN = "UNKNOWN"
RETRY_LIMIT_REACHED = "RETRY_LIMIT_REACHED"

errors = {
    STATUS_LOGIN_FAILED: {"code": 402,
                          "message": "We could not update your account because your username and/or password were"
                                     "reported to be incorrect. Please re-verify your username and password."},
    INVALID_MFA_INFO: {"code": 234,
                       "message": "We're sorry, the authentication information you  provided is incorrect. "
                                    "Please try again."},
    AGENT_DOWN: {"code": 235,
                 "message": "The agent is currently down for maintenance."},
    RETRY_LIMIT_REACHED: {"code": 236,
                            "message": "You have reached your maximum amount of login tries please wait 20 minutes."},
    STATUS_ACCOUNT_LOCKED: {"code": 407,
                            "message": "We could not update your account because it appears your <SITE_NAME> account"
                                         "has been locked. This usually results from too many unsuccessful login"
                                         "attempts in a short period of time. Please visit the site or contact its"
                                         "customer support to resolve this issue.  Once done, please update your"
                                         "account credentials in case they are changed."},
    UNKNOWN: {"code": 666,
              "message": "We have know the idea what went wrong the team is on to it."}

}


class MinerError(Exception):
    """Exception raised for errors in the input.
    """
    def __init__(self, name):
        self.name = name
        self.message = errors[name]['message']
        self.code = errors[name]['code']


class LoginError(MinerError):
    pass

