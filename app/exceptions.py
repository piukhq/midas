
class AgentException(Exception):
    code = None
    description = None
    name = None

    def __init__(self, description, code, name):
        self.description = description
        self.code = code
        self.name = name


def agent_abort(e):
    raise AgentException(e.message, e.code, e.name)


def unknown_abort(e):
    raise AgentException(str(e), 520, "Unknown Error")
