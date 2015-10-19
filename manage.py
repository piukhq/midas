#!/usr/bin/env python3
import os
from flask.ext.script import Manager, Shell, Server
from app import create_app

app = create_app()
manager = Manager(app)

# access python shell with context
manager.add_command("shell", Shell(make_context=lambda: {'app': app}), use_ipython=True)

# run the app
manager.add_command("runserver", Server(port=(os.getenv('FLASK_PORT') or 8000), host='127.0.0.2'))


HERE = os.path.abspath(os.path.dirname(__file__))
UNIT_TEST_PATH = os.path.join(HERE, 'app', 'tests', 'unit')


@manager.command
def test():
    """Run the tests."""
    import pytest
    exit_code = pytest.main([UNIT_TEST_PATH, '--verbose'])
    return exit_code


if __name__ == '__main__':
    manager.run()
