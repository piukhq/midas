from werkzeug.exceptions import HTTPException


class AgentException(HTTPException):
    code = None
    description = None
    name = None

    def __init__(self, description, code, name):
        self.description = description
        self.code = code
        self.name = name

    def get_response(self, environ):
        resp = super(AgentException, self).get_response(environ)
        resp.status = "%s %s" % (self.code, self.name.upper())
        return resp


def agent_abort(e):
    raise AgentException(e.message, e.code, e.name)


def unknown_abort(e):
    raise AgentException(str(e), 520, "Unknown Error")
