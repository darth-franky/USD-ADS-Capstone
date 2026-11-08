from pathlib import Path
import unittest

import pandas as pd


class Week4PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path("data/processed/ciso_day_ahead_features_2019_2025.csv")
        if not path.exists():
            raise unittest.SkipTest("Run scripts/build_week4_analysis.py first")
        cls.df = pd.read_csv(path)

    def test_full_hourly_series(self):
        self.assertEqual(len(self.df), 61368)
        self.assertEqual(self.df["timestamp_utc"].nunique(), 61368)

    def test_target_is_valid(self):
        self.assertEqual(self.df["raw_demand_mwh"].isna().sum(), 118)
        self.assertEqual(self.df["demand_clean_mwh"].isna().sum(), 0)
        self.assertGreaterEqual(self.df["demand_clean_mwh"].min(), 10000)
        self.assertEqual(int(self.df["author_imputed"].sum()), 38)

    def test_lags_are_past_values(self):
        self.assertAlmostEqual(
            self.df.loc[168, "demand_lag_168h"], self.df.loc[0, "demand_clean_mwh"]
        )
        self.assertAlmostEqual(
            self.df.loc[48, "demand_lag_48h"], self.df.loc[0, "demand_clean_mwh"]
        )

    def test_holdout_year_is_present(self):
        self.assertEqual((self.df["year"] == 2025).sum(), 8760)


if __name__ == "__main__":
    unittest.main()
