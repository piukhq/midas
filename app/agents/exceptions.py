"""
Error code notes:

https://developer.yodlee.com/FAQs/Error_Codes
https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
http://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

4xx client errors, custom error codes are in the range 432-440
5xx service errors, custom error codes are in the range 530-540
"""
STATUS_ACCOUNT_LOCKED = "STATUS_ACCOUNT_LOCKED"
STATUS_LOGIN_FAILED = "STATUS_LOGIN_FAILED"
INVALID_MFA_INFO = "INVALID_MFA_INFO"
END_SITE_DOWN = "END_SITE_DOWN"
UNKNOWN = "UNKNOWN"
RETRY_LIMIT_REACHED = "RETRY_LIMIT_REACHED"
IP_BLOCKED = "IP_BLOCKED"
TRIPPED_CAPTCHA = "TRIPPED_CAPTCHA"
PASSWORD_EXPIRED = "PASSWORD_EXPIRED"
WRONG_CREDENTIAL_TYPE = "WRONG_CREDENTIAL_TYPE"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
STATUS_REGISTRATION_FAILED = "STATUS_REGISTRATION_FAILED"
NO_SUCH_RECORD = "NO_SUCH_RECORD"
ACCOUNT_ALREADY_EXISTS = "ACCOUNT_ALREADY_EXISTS"
NOT_SENT = "NOT_SENT"
RESOURCE_LIMIT_REACHED = "RESOURCE_LIMIT_REACHED"
VALIDATION = "VALIDATION"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
SERVICE_CONNECTION_ERROR = "SERVICE_CONNECTION_ERROR"
PRE_REGISTERED_CARD = "PRE_REGISTERED_CARD"
LINK_LIMIT_EXCEEDED = "LINK_LIMIT_EXCEEDED"
CARD_NUMBER_ERROR = "CARD_NUMBER_ERROR"
CARD_NOT_REGISTERED = "CARD_NOT_REGISTERED"
GENERAL_ERROR = "GENERAL_ERROR"
JOIN_IN_PROGRESS = "JOIN_IN_PROGRESS"
JOIN_ERROR = "JOIN_ERROR"

errors = {
    VALIDATION: {"code": 401,
                 "message": "Validation of the request has failed.",
                 "name": "Failed validation"},
    STATUS_LOGIN_FAILED: {"code": 403,
                          "message": "We could not update your account because your username and/or password were "
                                     "reported to be incorrect. Please re-verify your username and password.",
                          "name": 'Invalid credentials'},
    PRE_REGISTERED_CARD: {"code": 406,
                          "message": "We could not link your account because this card does not exist yet in this "
                                     "loyalty scheme. Please join this loyalty scheme with those credentials and try "
                                     "again.",
                          "name": 'Pre-registered card'},
    INVALID_MFA_INFO: {"code": 432,
                       "message": "We're sorry, the authentication information you  provided is incorrect. "
                                  "Please try again.",
                       "name": "Invalid mfa"},
    RETRY_LIMIT_REACHED: {"code": 429,
                          "message": "You have reached your maximum amount of login tries please wait 15 minutes.",
                          "name": "Retry limit reached"},
    STATUS_ACCOUNT_LOCKED: {
        "code": 434,
        "message": "We could not update your account because it appears your account has been locked. This usually"
                   " results from too many unsuccessful login attempts in a short period of time. Please visit the site"
                   " or contact its customer support to resolve this issue. Once done, please update your account"
                   " credentials in case they are changed.",
        "name": "Account locked on end site"},
    WRONG_CREDENTIAL_TYPE: {
        "code": 435,
        "message": "One of the account credentials you have entered is the wrong type. For example, you may have"
                   " entered your card number instead of your barcode. Please correct this information and try again.",
        "name": "Wrong credential type entered"},
    CARD_NUMBER_ERROR: {
        "code": 436,
        "message": "Invalid card_number",
        "name": "Card number error"},
    LINK_LIMIT_EXCEEDED: {
        "code": 437,
        "message": "You can only Link one card per day.",
        "name": "Link Limit Exceeded"},
    CARD_NOT_REGISTERED: {
        "code": 438,
        "message": "Unknown Card number",
        "name": "Card not registered or Unknown"},
    GENERAL_ERROR: {
        "code": 439,
        "message": "General Error such as incorrect user details",
        "name": "General Error"},
    STATUS_REGISTRATION_FAILED: {
        "code": 440,
        "message": "The username and/or password you have entered were reported to be invalid. This may for reasons "
                   "such as the password being too short, or it requiring capital letters and numbers etc.",
        "name": 'Invalid credentials entered i.e password too short'},
    JOIN_IN_PROGRESS: {
        "code": 441,
        "message": "Join in progress",
        "name": "Join in progress"},
    NO_SUCH_RECORD: {"code": 444,
                     "message": "There is currently no account with the credentials you have provided.",
                     "name": "Account does not exist"},
    ACCOUNT_ALREADY_EXISTS: {"code": 445,
                             "message": "An account with this username/email already exists",
                             "name": "Account already exists"},
    RESOURCE_LIMIT_REACHED: {"code": 503,
                             "message": "there are currently too many balance requests running, please wait before "
                                        "trying again",
                             "name": "Resource limit reached"},
    END_SITE_DOWN: {"code": 530,
                    "message": "The scheme end site is currently down.",
                    "name": "End site down"},
    IP_BLOCKED: {"code": 531,
                 "message": "The end site is currently blocking this ip address",
                 "name": "IP blocked"},
    TRIPPED_CAPTCHA: {"code": 532,
                      "message": "The agent has tripped the scheme capture",
                      "name": "Tripped captcha"},
    PASSWORD_EXPIRED: {"code": 533,
                       "message": "We could not update your account because the end site requires that you reset your "
                                  "password. Please visit the site and resolve this issue before trying again.",
                       "name": "Password expired"},
    CONFIRMATION_REQUIRED: {"code": 534,
                            "message": "The end-site requires that you confirm some information before we can "
                                       "continue. Please log into your account on the end-site and follow through any "
                                       "confirmation steps shown, then try again.",
                            "name": "Confirmation required"},
    NOT_SENT: {"code": 535,
               "message": "Message was not sent",
               "name": "Message was not sent"},
    CONFIGURATION_ERROR: {"code": 536,
                          "message": "There is an error with the configuration or it was not possible to retrieve.",
                          "name": "Configuration error"},
    SERVICE_CONNECTION_ERROR: {"code": 537,
                               "message": "There was in issue connecting to an external service.",
                               "name": "Service connection error"},
    JOIN_ERROR: {
        "code": 538,
        "message": "A system error occurred during join.",
        "name": "General Error preventing join"},
    UNKNOWN: {"code": 520,
              "message": "We have no idea what went wrong the team is on to it.",
              "name": "An unknown error has occurred"},

}

SYSTEM_ACTION_REQUIRED = [
    END_SITE_DOWN, RETRY_LIMIT_REACHED, UNKNOWN, IP_BLOCKED, TRIPPED_CAPTCHA, NO_SUCH_RECORD, RESOURCE_LIMIT_REACHED,
    CONFIGURATION_ERROR, NOT_SENT, JOIN_ERROR
]


class AgentError(Exception):
    """Exception raised for errors in the input.
    """

    def __init__(self, name):
        self.name = errors[name]['name']
        self.message = errors[name]['message']
        self.code = errors[name]['code']

    def __str__(self):
        return "{0}: {1} code: {2}".format(self.name, self.message, self.code)


class LoginError(AgentError):
    pass


class RetryLimitError(AgentError):
    pass


class AgentModifiedError(Exception):
    pass


class RegistrationError(AgentError):
    pass
