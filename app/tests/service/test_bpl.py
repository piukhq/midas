import unittest
from app.agents.bpl import Trenette
from app.tests.service.logins import AGENT_CLASS_ARGUMENTS


class TestBPL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Trenette(*AGENT_CLASS_ARGUMENTS, scheme_slug="bpl-trenette")

    def test_register(self):
        credentials = {
            "email": "bpluser6@binktest.com",
            "first_name": "BPL",
            "last_name": "Smith"}
        self.agent.register(credentials)
