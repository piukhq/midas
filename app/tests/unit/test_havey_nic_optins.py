import unittest
from app.agents.harvey_nichols import HNOptInsSoapMessage
from lxml import etree


class TestHNOptins(unittest.TestCase):
    def setUp(self):
        pass

    def test_soap_message(self):
        sm = HNOptInsSoapMessage("12345678", "2018-12-01 19:45", "2018-12-01 19:42:12", True, True)
        soap_string = sm.optin_soap_message
        note_string = sm.audit_note
        print(soap_string)
        print(note_string)
        etree.fromstring(soap_string.encode('utf-8'))
        etree.fromstring(note_string.encode('utf-8'))
