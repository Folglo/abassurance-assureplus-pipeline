import tempfile
import unittest
from pathlib import Path

from abassurance import synthetic
from abassurance.extract import RAW_FILES, load_raw
from abassurance.pipeline import run_pipeline

TODAY = "2026-10-30"


class TestPipelineEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        synthetic.write_csv(
            cls.folder.name, seed=7, n_oracle=120, n_sqlserver=80, n_cross=10, n_internal=3
        )
        cls.result = run_pipeline(cls.folder.name, today=TODAY)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_all_files_are_written(self):
        self.assertEqual(
            {p.name for p in Path(self.folder.name).iterdir()}, set(RAW_FILES.values())
        )

    def test_no_row_disappears_without_a_log_entry(self):
        counts = self.result.row_counts
        removed = int((counts["rows_read"] - counts["rows_kept"]).sum())
        log = self.result.quality.to_frame()
        explained = int(log["reason"].isin(["duplicate_key", "orphan_parent_missing"]).sum())
        self.assertEqual(removed, explained)

    def test_unified_tables_have_both_sources(self):
        for table in (self.result.customers, self.result.contracts, self.result.payments):
            self.assertEqual(table["source"].nunique(), 2)

    def test_keys_are_unique_and_references_valid(self):
        self.assertTrue(self.result.customers["customer_key"].is_unique)
        self.assertTrue(
            self.result.contracts["customer_key"].isin(self.result.customers["customer_key"]).all()
        )
        self.assertTrue(
            self.result.claims["contract_key"].isin(self.result.contracts["contract_key"]).all()
        )

    def test_cross_source_duplicates_are_detected(self):
        cross = self.result.duplicates.query("source_a != source_b")
        self.assertGreaterEqual(len(cross), 10)

    def test_missing_file_stops_the_pipeline(self):
        with tempfile.TemporaryDirectory() as empty, self.assertRaises(FileNotFoundError):
            load_raw(empty)


if __name__ == "__main__":
    unittest.main()
