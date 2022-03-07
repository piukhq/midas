import unittest

from app.vouchers import generate_pending_voucher_code


class TestVouchers(unittest.TestCase):
    def test_generate_pending_voucher_code(self):
        self.assertEqual("Due:17thMar 2022", generate_pending_voucher_code(1647512390))
        self.assertEqual("Due: 7thMar 2022", generate_pending_voucher_code(1646648390))
