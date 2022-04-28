# import json
# from unittest import mock
# from unittest.mock import MagicMock

# import httpretty
from flask_testing import TestCase

# from app.agents.template_agent import TemplateAgent
from app.api import create_app

"""

Created from a template. Uncomment necessary imports.

"""


class TestTemplate(TestCase):
    def create_app(self):
        return create_app(self)

    def setUp(self):
        pass

    def test_join(self):
        pass

    def test_balance(self):
        pass
