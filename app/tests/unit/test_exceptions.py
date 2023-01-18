from unittest import TestCase

from requests import HTTPError

from app.exceptions import UnknownError, get_message_from_exception


class TestExceptions(TestCase):
    def test_get_message_from_none(self):
        message = get_message_from_exception(exception=None)
        self.assertEqual(None, message)

    def test_get_message_from_general_exception(self):
        message = get_message_from_exception(exception=Exception("Any old exception will do"))
        self.assertEqual("Any old exception will do", message)

    def test_get_message_from_specific_exception(self):
        message = get_message_from_exception(exception=UnknownError(exception=HTTPError("Any old exception will do")))
        self.assertEqual("Any old exception will do", message)

    def test_get_message_from_empty_exception(self):
        message = get_message_from_exception(UnknownError(exception=Exception()))
        self.assertEqual("An unknown error has occurred.", message)

    def test_default_system_action_required_attribute_is_overridden_to_true(self):
        error = UnknownError()
        assert error.system_action_required is True
