"""
Error code notes:

https://developer.yodlee.com/FAQs/Error_Codes
https://en.wikipedia.org/wiki/List_of_HTTP_codes
http://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

4xx client errors, custom error codes are in the range 432-440
5xx service errors, custom error codes are in the range 530-540
"""


def get_message_from_exception(exception):
    if exception is None:
        return None
    if len(exception.args) > 0:
        return str(exception.args[0])
    try:
        return exception.message
    except AttributeError:
        return None


class BaseError(Exception):
    code: int
    name: str
    generic_message: str
    system_action_required: bool = False

    def __init__(self, exception=None, message=None):
        self.exception = exception
        self.message = message or get_message_from_exception(self.exception) or self.generic_message

    def __str__(self):
        return f"{self.code} {self.name}: {self.message}"


class ValidationError(BaseError):
    code = 401
    name = "Failed validation"
    generic_message = "Validation of the request has failed."


class StatusLoginFailedError(BaseError):
    code = 403
    name = "Invalid credentials"
    generic_message = (
        "We could not update your account because your username and/or password "
        "were reported to be incorrect. Please re-verify your username and password."
    )


class PreRegisteredCardError(BaseError):
    code = 406
    name = "Pre-registered card"
    generic_message = (
        "We could not link your account because this card does not exist yet in this loyalty "
        "scheme. Please join this loyalty scheme with those credentials and try again."
    )


class RetryLimitReachedError(BaseError):
    code = 429
    name = "Retry limit reached"
    generic_message = "You have reached your maximum amount of login tries. Please wait 15 minutes."
    system_action_required = True


class InvalidMFAInfoError(BaseError):
    code = 432
    name = "Invalid MFA"
    generic_message = "We're sorry, the authentication information you provided is incorrect. Please try again."


class StatusAccountLockedError(BaseError):
    code = 434
    name = "Account locked on end site"
    generic_message = (
        "We could not update your account because it appears your account has been locked. This usually results "
        "from too many unsuccessful login attempts in a short period of time. Please visit the site or contact "
        "its customer support to resolve this issue. Once done, please update your account credentials in case "
        "they are changed."
    )


class CardNumberError(BaseError):
    code = 436
    name = "Card not registered or Unknown"
    generic_message = "Unknown card number."


class LinkLimitExceededError(BaseError):
    code = 437
    name = "Card not registered or Unknown"
    generic_message = "Unknown Card number."


class CardNotRegisteredError(BaseError):
    code = 438
    name = "Card not registered or Unknown"
    generic_message = "Unknown Card number."


class GeneralError(BaseError):
    code = 439
    name = "General error"
    generic_message = "General error such as incorrect user details."


class StatusRegistrationFailedError(BaseError):
    code = 440
    name = "Status registration failed"
    generic_message = (
        "The username and/or password you have entered were reported to be invalid. This may due "
        "to password validation - it's too short, it requires capital letters and numbers, etc."
    )


class JoinInProgressError(BaseError):
    code = 441
    name = "Join in progress"
    generic_message = "Join in progress."


class NoSuchRecordError(BaseError):
    code = 444
    name = "Account does not exist"
    generic_message = "There is currently no account with the credentials you have provided."
    system_action_required = True


class AccountAlreadyExistsError(BaseError):
    code = 445
    name = "Account already exists"
    generic_message = "An account with this username/email already exists."


class SchemeRequestedDeleteError(BaseError):
    code = 447
    name = "Scheme requested account deletion"
    generic_message = "The scheme has requested this account should be deleted."


class UnknownError(BaseError):
    code = 520
    name = "Unknown error"
    generic_message = "An unknown error has occurred."
    system_action_required = True


class EndSiteDownError(BaseError):
    code = 530
    name = "End site down"
    generic_message = "The scheme end site is currently down."
    system_action_required = True


class IPBlockedError(BaseError):
    code = 531
    name = "IP blocked"
    generic_message = "The end site is currently blocking this ip address."
    system_action_required = True


class PasswordExpiredError(BaseError):
    code = 533
    name = "Password expired"
    generic_message = (
        "We could not update your account because the end site requires that you reset your password. "
        "Please visit the site and resolve this issue before trying again."
    )


class NotSentError(BaseError):
    code = 535
    name = "Message was not sent"
    generic_message = "Message was not sent."
    system_action_required = True


class ConfigurationError(BaseError):
    code = 536
    name = "Configuration error"
    generic_message = "There is an error with the configuration or it was not possible to retrieve."
    system_action_required = True


class ServiceConnectionError(BaseError):
    code = 537
    name = "Service connection error"
    generic_message = "There was in issue connecting to an external service."


class JoinError(BaseError):
    code = 538
    name = "General error preventing join"
    generic_message = "A system error occurred during join."
    system_action_required = True
