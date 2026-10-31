import unittest

import pandas as pd

from abassurance.clean import parse_dates


class SilentDateErrorsTest(unittest.TestCase):
    """Bug D3-Q3 : une date illisible ne doit jamais disparaître sans motif de rejet."""

    def setUp(self):
        self.dates = pd.Series(["1985-03-12", "12/03/1985", "12-03-85", "pas une date", None, ""])

    def test_naive_conversion_loses_dates_without_explanation(self):
        naive = pd.to_datetime(self.dates, errors="coerce", format="%Y-%m-%d")
        self.assertGreater(naive.isna().sum(), 0)

    def test_every_lost_date_has_a_rejection_reason(self):
        parsed, reasons = parse_dates(self.dates, today="2026-10-31")
        self.assertEqual(parsed.isna().sum(), reasons.notna().sum())

    def test_reasons_are_the_expected_ones(self):
        _, reasons = parse_dates(self.dates, today="2026-10-31")
        self.assertEqual(
            list(reasons), [None, None, "unparseable", "unparseable", "missing", "missing"]
        )

    def test_valid_dates_are_kept(self):
        parsed, _ = parse_dates(self.dates, today="2026-10-31")
        self.assertEqual(parsed.iloc[0], pd.Timestamp("1985-03-12"))
        self.assertEqual(parsed.iloc[1], pd.Timestamp("1985-03-12"))


if __name__ == "__main__":
    unittest.main()
