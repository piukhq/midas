import unittest
from app.agents.harvey_nichols import HNOptInsSoapMessage
from lxml import etree


class TestHNOptins(unittest.TestCase):
    def setUp(self):
        pass

    def test_soap_message(self):
        sm = HNOptInsSoapMessage("12345678")
        sm.add_consent("EMAIL", True , "2018-12-01 19:45")
        sm.add_consent("PUSH", True, "2018-12-01 19:42:12")
        soap_string = sm.optin_soap_message
        note_string = sm.audit_note
        print(soap_string)
        print(note_string)
        etree.fromstring(soap_string.encode('utf-8'))
        etree.fromstring(note_string.encode('utf-8'))

    def test_soap_message_consent_order(self):
        sm = HNOptInsSoapMessage("12345678")
        sm.add_consent("EMAIL", True , "2018-12-01 19:45")
        sm.add_consent("PUSH", True, "2018-12-01 19:42:12")

        sm2 = HNOptInsSoapMessage("12345678")
        sm2.note_id = sm.note_id      # make sure random id is the same so messages should be identical
        sm2.add_consent("PUSH", True, "2018-12-01 19:42:12")
        sm2.add_consent("EMAIL", True, "2018-12-01 19:45")

        self.assertEqual(sm.optin_soap_message, sm2.optin_soap_message)
        self.assertEqual(sm.audit_note, sm2.audit_note)
        soap_string = sm.optin_soap_message

