import unittest

import pandas as pd

from abassurance import synthetic


class TestSyntheticData(unittest.TestCase):
    def test_generation_is_reproducible(self):
        first = synthetic.generate(seed=1, n_oracle=60, n_sqlserver=40, n_cross=5, n_internal=2)
        second = synthetic.generate(seed=1, n_oracle=60, n_sqlserver=40, n_cross=5, n_internal=2)
        for name in first:
            pd.testing.assert_frame_equal(first[name], second[name])

    def test_columns_follow_the_annex_schemas(self):
        tables = synthetic.generate(seed=1, n_oracle=60, n_sqlserver=40, n_cross=5, n_internal=2)
        self.assertEqual(len(tables["ab_client"].columns), 11)
        self.assertEqual(len(tables["ap_users"].columns), 10)
        self.assertIn("AP_FRAUD_SCORE", tables["ap_claims"].columns)
        self.assertIn("AB_NUM_FISCAL", tables["ab_client"].columns)


if __name__ == "__main__":
    unittest.main()
