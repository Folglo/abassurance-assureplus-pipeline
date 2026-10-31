import unittest

import pandas as pd

from abassurance.quality import QualityLog


class TestQualityLog(unittest.TestCase):
    def test_empty_log(self):
        log = QualityLog()
        self.assertTrue(log.to_frame().empty)
        self.assertTrue(log.summary().empty)

    def test_only_rows_with_a_reason_are_recorded(self):
        log = QualityLog()
        ids = pd.Series([1, 2, 3])
        log.record(
            "customers",
            "AbAssurance",
            "email",
            ids,
            pd.Series(["a", "b", "c"]),
            pd.Series([None, "invalid_format", "missing"]),
        )
        frame = log.to_frame()
        self.assertEqual(list(frame["row_id"]), ["2", "3"])
        self.assertEqual(len(log.summary()), 2)

    def test_nothing_recorded_when_no_reason(self):
        log = QualityLog()
        log.record("t", "s", "c", pd.Series([1]), pd.Series(["x"]), pd.Series([None]))
        self.assertTrue(log.to_frame().empty)


if __name__ == "__main__":
    unittest.main()
