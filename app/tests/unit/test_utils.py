import unittest
from decimal import Decimal
from app.utils import extract_decimal, generate_random_key, minify_number, create_error_response, get_headers


class TestUtils(unittest.TestCase):

    def test_extract_decimal(self):
        self.assertEqual(extract_decimal("sdfg -23.33 dfg"), Decimal("-23.33"))
        self.assertEqual(extract_decimal("sdfg 23.33 dfg"), Decimal("23.33"))
        self.assertEqual(extract_decimal("233"), Decimal("233"))
        self.assertEqual(extract_decimal("23.1 hhh"), Decimal("23.1"))
        self.assertEqual(extract_decimal("24,412.51"), Decimal("24412.51"))

    def test_generate_random_key(self):
        self.assertEqual(type(generate_random_key(1)), bytes)

    def test_minify_number(self):
        test_cases = [
            (0, '0'),
            (10, '10'),
            (501, '501'),
            (5214, '5214'),
            (60563, '60k'),
            (5329582, '5M'),
            (59235820935, '59B'),
            (24135802938509, '24T')
        ]

        for test_case in test_cases:
            n = minify_number(test_case[0])
            self.assertEqual(n, test_case[1])

    def test_create_error_response(self):
        response_json = create_error_response("NOT_SENT", "This is a test error")

        self.assertIn('NOT_SENT', response_json)

    def test_get_headers(self):
        headers = get_headers("success")

        self.assertEqual(headers['transaction'], "success")
