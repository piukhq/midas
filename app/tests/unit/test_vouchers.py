import unittest

from app.vouchers import generate_pending_voucher_code


class TestVouchers(unittest.TestCase):
    def test_generate_pending_voucher_code(self):
        self.assertEqual(generate_pending_voucher_code(1647512390), "Due:17thMar 2022")
        self.assertEqual(generate_pending_voucher_code(1646648390), "Due: 7thMar 2022")
