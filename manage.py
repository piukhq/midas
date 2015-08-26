#!/usr/bin/env python
import os
from flask.ext.script import Manager, Shell, Server
from app import app


manager = Manager(app)

# access python shell with context
manager.add_command("shell", Shell(make_context=lambda: {'app': app}), use_ipython=True)

# run the app
manager.add_command("startserver", Server(port=(os.getenv('FLASK_PORT') or 5000), host='0.0.0.0'))


if __name__ == '__main__':
    manager.run()
