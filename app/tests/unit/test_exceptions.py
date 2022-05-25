from unittest import TestCase

from requests import HTTPError

from app.exceptions import get_message_from_exception


class TestExceptions(TestCase):

    def test_get_message_from_general_exception(self):
        message = get_message_from_exception(exception=Exception("Any old exception will do"))
        self.assertEqual("Any old exception will do", message)

    # def test_get_message_from_specific_exception(self):
    #     message = get_message_from_exception(exception=HTTPError())
    #     self.assertEqual(None, message)

    def test_get_message_from_none(self):
        message = get_message_from_exception(exception=None)
        self.assertEqual(None, message)
