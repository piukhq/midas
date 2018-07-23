import unittest
from app.agents.harvey_nichols import HNOptInsSoapMessage
import lxml.etree as etree


def get_tag_analyis(tree):
    concern_list = ("created", "customerId", "preferenceId", "value", "isPrivate", "noteId", "notes")
    tag_list = []
    ret_dict = {}
    group = "root"
    ret_dict[group] = {}
    for element in tree.iter():
        tag_list.append(element.tag)
        if "optionPathId" in element.tag:
            group = element.text
            ret_dict[group] = {}
        else:
            for concern in concern_list:
                if concern in element.tag:
                    ret_dict[group][concern] = element.text
    return tag_list, ret_dict


class TestHNOptins(unittest.TestCase):
    def setUp(self):
        pass

    def test_soap_message(self):
        sm = HNOptInsSoapMessage("12345678")
        sm.add_consent("EMAIL", True, "2018-12-01 19:45")
        sm.add_consent("PUSH", True, "2018-12-01 19:42:12")
        soap_string = sm.optin_soap_message
        note_string = sm.audit_note

        sm_doc = etree.fromstring(soap_string.encode('utf-8'))
        etree.fromstring(note_string.encode('utf-8'))
        sm_tree = etree.ElementTree(sm_doc)

        note_doc = etree.fromstring(note_string.encode('utf-8'))
        note_tree = etree.ElementTree(note_doc)

        tag_list, items_dict = get_tag_analyis(sm_tree)
        expected_tags = [
            "{http://schemas.xmlsoap.org/soap/envelope/}Envelope",
            "{http://schemas.xmlsoap.org/soap/envelope/}Body",
            "{http://www.enactor.com/retail}saveCustomerPreferenceMap",
            "{http://www.enactor.com/retail}userId",
            "{http://www.enactor.com/retail}customerPreferenceMap",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value",
            "item",
            "{http://www.enactor.com/retail}customerPreference",
            "{http://www.enactor.com/retail}optionPathId",
            "{http://www.enactor.com/retail}created",
            "{http://www.enactor.com/retail}optionSetId",
            "{http://www.enactor.com/retail}groupId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}preferenceId",
            "{http://www.enactor.com/retail}value"
            ]
        self.assertListEqual(expected_tags, tag_list)
        expected_dict = {'root': {},
                         'EMAIL:EMAIL_OPTIN': {
                             'created': '2018-12-01T19:45:00',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPREMAIL:EMAIL_OPTIN',
                             'value': 'true'
                         },
                         'EMAIL:EMAIL_OPTIN_DATETIME': {
                             'created': '2018-12-01T19:45:00',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPREMAIL:EMAIL_OPTIN_DATETIME',
                             'value': '2018-12-01T19:45:00'
                         },
                         'EMAIL:EMAIL_OPTIN_SOURCE': {
                             'created': '2018-12-01T19:45:00',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPREMAIL:EMAIL_OPTIN_SOURCE',
                             'value': 'BINK_APP'
                         },
                         'PUSH:PUSH_OPTIN': {
                             'created': '2018-12-01T19:42:12',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPRPUSH:PUSH_OPTIN',
                             'value': 'true'
                         },
                         'PUSH:PUSH_OPTIN_DATETIME': {
                             'created': '2018-12-01T19:42:12',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPRPUSH:PUSH_OPTIN_DATETIME',
                             'value': '2018-12-01T19:42:12'
                         },
                         'PUSH:PUSH_OPTIN_SOURCE': {
                             'created': '2018-12-01T19:42:12',
                             'customerId': '12345678',
                             'preferenceId': '12345678GDPRPUSH:PUSH_OPTIN_SOURCE',
                             'value': 'BINK_APP'}
                         }

        self.assertDictEqual(expected_dict, items_dict)

        tag_list, items_dict = get_tag_analyis(note_tree)
        expected_tags = [
            "{http://schemas.xmlsoap.org/soap/envelope/}Envelope",
            "{http://schemas.xmlsoap.org/soap/envelope/}Body",
            "{http://www.enactor.com/crm}saveCustomerNote",
            "{http://www.enactor.com/retail}customerNote",
            "{http://www.enactor.com/retail}userId",
            "{http://www.enactor.com/retail}customerId",
            "{http://www.enactor.com/retail}isPrivate",
            "{http://www.enactor.com/retail}noteId",
            "{http://www.enactor.com/retail}notes"
        ]
        self.assertListEqual(expected_tags, tag_list)
        expected_dict = {
            'root': {
                'customerId': '12345678',
                'isPrivate': 'false',
                'noteId': sm.note_id,
                'notes': 'Preference changes: EMAIL_OPTIN set to true |'
                         ' EMAIL_OPTIN_DATETIME set to 2018-12-01T19:45:00 |'
                         ' EMAIL_OPTIN_SOURCE set to BINK_APP | PUSH_OPTIN set to true |'
                         ' PUSH_OPTIN_DATETIME set to 2018-12-01T19:42:12 | PUSH_OPTIN_SOURCE set to BINK_APP'
            }
        }
        self.assertDictEqual(expected_dict, items_dict)

    def test_soap_message_consent_order(self):
        sm = HNOptInsSoapMessage("12345678", )
        sm.add_consent("EMAIL", True , "2018-12-01 19:45")
        sm.add_consent("PUSH", True, "2018-12-01 19:42:12")

        sm2 = HNOptInsSoapMessage("12345678")
        sm2.note_id = sm.note_id      # make sure random id is the same so messages should be identical
        sm2.add_consent("PUSH", True, "2018-12-01 19:42:12")
        sm2.add_consent("EMAIL", True, "2018-12-01 19:45")

        self.assertEqual(sm.optin_soap_message, sm2.optin_soap_message)
        self.assertEqual(sm.audit_note, sm2.audit_note)


