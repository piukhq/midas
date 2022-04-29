"""
Error code notes:

https://developer.yodlee.com/FAQs/Error_Codes
https://en.wikipedia.org/wiki/List_of_HTTP_codes
http://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

4xx client errors, custom error codes are in the range 432-440
5xx service errors, custom error codes are in the range 530-540
"""


class AgentException(Exception):
    def __init__(self, error):
        self.status_code = return_error_code(error)


class UnknownException(Exception):
    def __init__(self, error):
        self.status_code = return_error_code(error)


def return_error_code(exception):
    try:
        return exception.code
    except AttributeError:
        # Return unknown error status code
        return 520


class BaseError(Exception):
    """Exception raised for errors in the input."""

    def __init__(self):
        self.name: str = ""
        self.message: str = ""
        self.code: int = None
        self.response = None
        self.system_action_required = False

    def __str__(self):
        return f"{self.code} {self.name}: {self.message}"


class ValidationError(BaseError):
    def __init__(self, response=None):
        self.code = 401
        self.name = "Failed validation"
        self.message = "Validation of the request has failed."


class StatusLoginFailedError(BaseError):
    def __init__(self, response=None):
        super().__init__()
        self.code = 403
        self.status_code = 403
        self.name = "Invalid credentials"
        self.message = """We could not update your account because your username and/or password 
        were reported to be incorrect. Please re-verify your username and password."""
        self.response = response


class PreRegisteredCardError(BaseError):
    def __init__(self, response=None):
        self.code = 406
        self.name = "Pre-registered card"
        self.message = """We could not link your account because this card does not exist yet in 
        this loyalty scheme. Please join this loyalty scheme with those credentials and try again."""
        self.response = response


class RetryLimitReachedError(BaseError):
    def __init__(self, response=None):
        self.code = 429
        self.name = "Retry limit reached"
        self.message = "You have reached your maximum amount of login tries. Please wait 15 minutes."
        self.system_action_required = True
        self.response = response


class StatusAccountLockedError(BaseError):
    def __init__(self, response=None):
        self.code = 434
        self.name = "Account locked on end site"
        self.message = """We could not update your account because it appears your account has been 
        locked. This usually results from too many unsuccessful login attempts in a short period of 
        time. Please visit the site or contact its customer support to resolve this issue. Once done, 
        please update your account credentials in case they are changed."""


class WrongCredentialTypeError(BaseError):
    def __init__(self, response=None):
        self.code = 435
        self.name = "Wrong credential type entered"
        self.message = """One of the account credentials you have entered is the wrong type. 
        For example, you may have entered your card number instead of your barcode. Please 
        correct this information and try again."""


class CardNumberError(BaseError):
    def __init__(self, response=None):
        self.code = 438
        self.name = "Card not registered or Unknown"
        self.message = "Unknown Card number."
        self.response = response


class LinkLimitExceededError(BaseError):
    def __init__(self, response=None):
        self.code = 438
        self.name = "Card not registered or Unknown"
        self.message = "Unknown Card number."
        self.response = response


class CardNotRegisteredError(BaseError):
    def __init__(self, response=None):
        self.code = 438
        self.name = "Card not registered or Unknown"
        self.message = "Unknown Card number."
        self.response = response


class GeneralError(BaseError):
    def __init__(self, response=None):
        self.code = 439
        self.name = "General Error"
        self.message = "General Error such as incorrect user details."
        self.response = response


class StatusRegistrationFailedError(BaseError):
    def __init__(self, response=None):
        self.code = 440
        self.name = "Join in progress"
        self.message = """The username and/or password you have entered were reported to be invalid. 
        This may due to password validation - it's too short, it requires capital letters and numbers, etc."""


class JoinInProgressError(BaseError):
    def __init__(self, response=None):
        self.code = 441
        self.name = "Join in progress"
        self.message = "Join in progress."
        self.response = response


class NoSuchRecordError(BaseError):
    def __init__(self, response=None):
        self.code = 444
        self.name = "Account does not exist"
        self.message = "There is currently no account with the credentials you have provided."
        self.system_action_required = True
        self.response = response


class AccountAlreadyExistsError(BaseError):
    def __init__(self, response=None):
        self.code = 445
        self.name = "Account already exists"
        self.message = "An account with this username/email already exists."
        self.response = response


class SchemeRequestedDeleteError(BaseError):
    def __init__(self, response=None):
        self.code = 447
        self.name = "Scheme requested account deletion"
        self.message = "The scheme has requested this account should be deleted."


class ResourceLimitReachedError(BaseError):
    def __init__(self, response=None):
        self.code = 503
        self.name = "Resource limit reached"
        self.message = "There are currently too many balance requests running. Please wait before trying again."
        self.system_action_required = True


class EndSiteDownError(BaseError):
    def __init__(self, response=None):
        self.code = 530
        self.name = "End site down"
        self.message = "The scheme end site is currently down."
        self.system_action_required = True


class IPBlockedError(BaseError):
    def __init__(self, response=None):
        self.code = 531
        self.name = "IP blocked"
        self.message = "The end site is currently blocking this ip address."
        self.system_action_required = True


class PasswordExpiredError(BaseError):
    def __init__(self, response=None):
        self.code = 533
        self.name = "Password expired"
        self.message = """We could not update your account because the end site requires that 
        you reset your password. Please visit the site and resolve this issue before trying again."""


class NotSentError(BaseError):
    def __init__(self, response=None):
        self.code = 535
        self.name = "Message was not sent"
        self.message = "Message was not sent."
        self.system_action_required = True
        self.response = response


class ConfigurationError(BaseError):
    def __init__(self, response=None):
        self.code = 536
        self.name = "Configuration error"
        self.message = "There is an error with the configuration or it was not possible to retrieve."
        self.system_action_required = True


class ServiceConnectionError(BaseError):
    def __init__(self, response=None):
        self.code = 537
        self.name = "Service connection error"
        self.message = "There was in issue connecting to an external service."


class JoinError(BaseError):
    def __init__(self, response=None):
        self.code = 538
        self.name = "General Error preventing join"
        self.message = "A system error occurred during join."
        self.system_action_required = True
        self.response = response


class UnknownError(BaseError):
    def __init__(self, response=None):
        self.code = 520
        self.name = "Invalid mfa"
        self.message = "We have no idea what went wrong - the team is on it."
        self.system_action_required = True
        self.response = response


# class InvalidMFAInfoError(AgentError):
#     def __init__(self, response=None):
#         self.code = 438
#         self.name = "Invalid MFA"
#         self.message = "We're sorry, the authentication information you provided is incorrect. Please try again."


# class ConfirmationRequiredError(AgentError):
#     def __init__(self, response=None):
#         self.code = 534
#         self.name = "Confirmation required"
#         self.message = """The end-site requires that you confirm some information before we
#         can continue. Please log into your account on the end-site and follow through any
#         confirmation steps shown, then try again."""


# class TrippedCaptchaError(AgentError):
#     def __init__(self, response=None):
#         self.code = 532
#         self.name = "Tripped captcha"
#         self.message = "The agent has tripped the scheme capture."
#         self.system_action_required = True


class AgentModifiedError(Exception):
    pass


class UnauthorisedError(Exception):
    pass
