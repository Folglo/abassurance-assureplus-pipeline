import unittest

import pandas as pd

from abassurance import clean


class TestTextCleaning(unittest.TestCase):
    def test_to_ascii_removes_accents(self):
        self.assertEqual(clean.to_ascii("Hélène"), "Helene")

    def test_name_key_ignores_order_case_and_accents(self):
        self.assertEqual(clean.name_key("Hélène", "DUPONT"), clean.name_key("dupont", "helene"))

    def test_normalize_name_handles_missing(self):
        self.assertEqual(clean.normalize_name(None), "")

    def test_clean_text_trims_and_flags_empty(self):
        values, reasons = clean.clean_text(pd.Series(["  Jean   Paul ", "  ", None]))
        self.assertEqual(values[0], "Jean Paul")
        self.assertEqual(list(reasons[1:]), ["missing", "missing"])


class TestEmailPhoneZip(unittest.TestCase):
    def test_email_lowercased_and_invalid_rejected(self):
        values, reasons = clean.clean_email(pd.Series(["A.B@Mail.FR", "a.b#mail.fr", None]))
        self.assertEqual(values[0], "a.b@mail.fr")
        self.assertEqual(reasons[1], "invalid_format")
        self.assertEqual(reasons[2], "missing")

    def test_phone_formats_are_unified(self):
        raw = pd.Series(["06 12 34 56 78", "+33 6 12 34 56 78", "06.12.34.56.78", "0033612345678"])
        values, reasons = clean.clean_phone(raw)
        self.assertTrue((values == "0612345678").all())
        self.assertTrue(reasons.isna().all())

    def test_phone_invalid_and_missing(self):
        _, reasons = clean.clean_phone(pd.Series(["123", None]))
        self.assertEqual(list(reasons), ["invalid_format", "missing"])

    def test_zip_keeps_leading_zero(self):
        values, reasons = clean.clean_zip(pd.Series(["6000", "75011", "ABCDE", None]))
        self.assertEqual(list(values[:2]), ["06000", "75011"])
        self.assertEqual(list(reasons[2:]), ["invalid_format", "missing"])
