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


class TestParseDates(unittest.TestCase):
    TODAY = "2026-10-30"

    def parse(self, values, **options):
        return clean.parse_dates(pd.Series(values), today=self.TODAY, **options)

    def test_accepted_formats(self):
        dates, reasons = self.parse(["1985-03-07", "12/03/1985", "2020-01-05 10:30:00"])
        self.assertEqual(
            list(dates),
            [
                pd.Timestamp("1985-03-07"),
                pd.Timestamp("1985-03-12"),
                pd.Timestamp("2020-01-05 10:30:00"),
            ],
        )
        self.assertTrue(reasons.isna().all())

    def test_invalid_date_is_explained_not_silent(self):
        dates, reasons = self.parse(["1985-13-45"])
        self.assertTrue(pd.isna(dates[0]))
        self.assertEqual(reasons[0], "unparseable")

    def test_missing_dates(self):
        _, reasons = self.parse(["", None])
        self.assertEqual(list(reasons), ["missing", "missing"])

    def test_out_of_range_dates(self):
        dates, reasons = self.parse(["1850-01-01", "2200-01-01"])
        self.assertEqual(list(reasons), ["out_of_range", "out_of_range"])
        self.assertTrue(dates.isna().all())

    def test_future_allowed_for_contract_end(self):
        dates, reasons = self.parse(["2030-01-01"], allow_future=True)
        self.assertEqual(dates[0], pd.Timestamp("2030-01-01"))
        self.assertTrue(reasons.isna().all())

    def test_today_in_the_afternoon_is_valid(self):
        _, reasons = self.parse(["2026-10-30 15:00:00"])
        self.assertTrue(reasons.isna().all())


class TestParseNumbers(unittest.TestCase):
    def test_decimal_comma_and_reasons(self):
        values, reasons = clean.parse_numbers(pd.Series(["12,5", "abc", None, "-3"]), minimum=0)
        self.assertEqual(values[0], 12.5)
        self.assertEqual(list(reasons[1:]), ["not_a_number", "missing", "out_of_range"])
        self.assertTrue(values[1:].isna().all())

    def test_maximum(self):
        _, reasons = clean.parse_numbers(pd.Series(["150"]), maximum=100)
        self.assertEqual(reasons[0], "out_of_range")


class TestMapValues(unittest.TestCase):
    def test_mapping_is_case_insensitive_and_flags_unknown(self):
        values, reasons = clean.map_values(pd.Series(["actif", "XX", None]), {"ACTIF": "active"})
        self.assertEqual(list(values), ["active", "unknown", "unknown"])
        self.assertEqual(list(reasons[1:]), ["unmapped_value", "missing"])


if __name__ == "__main__":
    unittest.main()
