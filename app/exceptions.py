"""
Error code notes:

https://developer.yodlee.com/FAQs/Error_Codes
https://en.wikipedia.org/wiki/List_of_HTTP_codes
http://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

4xx client errors, custom error codes are in the range 432-440
5xx service errors, custom error codes are in the range 530-540
"""


class BaseError(Exception):
    """Exception raised for errors in the input."""

    def __init__(self):
        self.name: str = ""
        self.message: str = ""
        self.code: int = None
        self.system_action_required = False
        self.response = None

    def __str__(self):
        return f"{self.code} {self.name}: {self.message}"


class ValidationError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 401
        self.name = "Failed validation"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Validation of the request has failed."


class StatusLoginFailedError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 403
        self.status_code = 403
        self.name = "Invalid credentials"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "We could not update your account because your username and/or password "
            "were reported to be incorrect. Please re-verify your username and password."
        )


class PreRegisteredCardError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 406
        self.name = "Pre-registered card"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "We could not link your account because this card does not exist yet in this "
            "loyalty scheme. Please join this loyalty scheme with those credentials and try again."
        )


class RetryLimitReachedError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 429
        self.name = "Retry limit reached"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "You have reached your maximum amount of login tries. Please wait 15 minutes."
        )
        self.system_action_required = True


class InvalidMFAInfoError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 432
        self.name = "Invalid MFA"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "We're sorry, the authentication information you provided is incorrect. Please try again."
        )


class StatusAccountLockedError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 434
        self.name = "Account locked on end site"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "We could not update your account because it appears your account has been locked. "
            "This usually results from too many unsuccessful login attempts in a short period of time. "
            "Please visit the site or contact its customer support to resolve this issue. Once done, "
            "please update your account credentials in case they are changed."
        )


class CardNumberError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 436
        self.name = "Card not registered or Unknown"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Unknown card number."


class LinkLimitExceededError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 437
        self.name = "Card not registered or Unknown"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Unknown Card number."


class CardNotRegisteredError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 438
        self.name = "Card not registered or Unknown"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Unknown Card number."


class GeneralError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 439
        self.name = "General error"
        self.exception = exception
        self.message = (
            message or get_message_from_exception(exception) or "General error such as incorrect user details."
        )


class StatusRegistrationFailedError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 440
        self.name = "Status registration failed"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "The username and/or password you have entered were reported to be invalid. "
            "This may due to password validation - it's too short, it requires capital letters "
            "and numbers, etc."
        )


class JoinInProgressError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 441
        self.name = "Join in progress"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Join in progress."


class NoSuchRecordError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 444
        self.name = "Account does not exist"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "There is currently no account with the credentials you have provided."
        )
        self.system_action_required = True


class AccountAlreadyExistsError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 445
        self.name = "Account already exists"
        self.exception = exception
        self.message = (
            message or get_message_from_exception(exception) or "An account with this username/email already exists."
        )


class SchemeRequestedDeleteError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 447
        self.name = "Scheme requested account deletion"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "The scheme has requested this account should be deleted."
        )


def get_message_from_exception(exception):
    if exception:
        return str(exception.args[0])
    return None


class UnknownError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 520
        self.name = "Unknown error"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "An unknown error has occurred."
        self.system_action_required = True


class EndSiteDownError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 530
        self.name = "End site down"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "The scheme end site is currently down."
        self.system_action_required = True


class IPBlockedError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 531
        self.name = "IP blocked"
        self.exception = exception
        self.message = (
            message or get_message_from_exception(exception) or "The end site is currently blocking this ip address."
        )
        self.system_action_required = True


class PasswordExpiredError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 533
        self.name = "Password expired"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "We could not update your account because the end site requires that you reset "
            "your password. Please visit the site and resolve this issue before trying again."
        )


class NotSentError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 535
        self.name = "Message was not sent"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "Message was not sent."
        self.system_action_required = True


class ConfigurationError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 536
        self.name = "Configuration error"
        self.exception = exception
        self.message = (
            message
            or get_message_from_exception(exception)
            or "There is an error with the configuration or it was not possible to retrieve."
        )
        self.system_action_required = True


class ServiceConnectionError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 537
        self.name = "Service connection error"
        self.exception = exception
        self.message = (
            message or get_message_from_exception(exception) or "There was in issue connecting to an external service."
        )


class JoinError(BaseError):
    def __init__(self, exception=None, message=None):
        super().__init__()
        self.code = 538
        self.name = "General error preventing join"
        self.exception = exception
        self.message = message or get_message_from_exception(exception) or "A system error occurred during join."
        self.system_action_required = True
