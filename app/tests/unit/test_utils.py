import unittest
from decimal import Decimal
from app.utils import extract_decimal, generate_random_key


class TestUtils(unittest.TestCase):
    def test_extract_decimal(self):
        self.assertEqual(extract_decimal("sdfg -23.33 dfg"), Decimal("-23.33"))
        self.assertEqual(extract_decimal("sdfg 23.33 dfg"), Decimal("23.33"))
        self.assertEqual(extract_decimal("233"), Decimal("233"))
        self.assertEqual(extract_decimal("23.1 hhh"), Decimal("23.1"))
        self.assertEqual(extract_decimal("24,412.51"), Decimal("24412.51"))

    def test_generate_random_key(self):
        self.assertEqual(type(generate_random_key(1)), bytes)
