
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
