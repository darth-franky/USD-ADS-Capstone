"""Week 4 regression checks. Run from the project root after building the CSV."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_week4_analysis import add_leakage_safe_features, font


class FeatureLogicTests(unittest.TestCase):
    """Unit checks that do not depend on the downloaded EIA workbook."""

    def test_font_fallback(self):
        self.assertIsNotNone(font(16))
        self.assertIsNotNone(font(16, bold=True))

    def test_cutoff_and_history_across_dst(self):
        # A self-contained hourly history covering both 2024 DST transitions.
        utc = pd.date_range('2024-03-01', '2024-11-15', freq='h', tz='UTC')
        local = utc.tz_convert('America/Los_Angeles')
        frame = pd.DataFrame({
            'timestamp_utc': utc,
            'timestamp_local': local,
            'operating_date': local.date.astype(str),
            'demand_clean_mwh': np.arange(len(utc), dtype=float) + 20000.0,
        })
        features = add_leakage_safe_features(frame)
        for target_date in ['2024-03-11', '2024-11-04', '2024-06-15']:
            rows = features.loc[features['operating_date'].eq(target_date)]
            self.assertGreater(len(rows), 0)
            cutoff = pd.Timestamp(rows['forecast_cutoff_local'].iloc[0])
            self.assertEqual(cutoff.hour, 12)
            self.assertEqual(cutoff.date(), (pd.Timestamp(target_date) - pd.Timedelta(days=1)).date())
            self.assertEqual(str(cutoff.tzinfo), 'UTC-07:00' if target_date in ('2024-03-11','2024-06-15') else 'UTC-08:00')
            history = frame.loc[
                (frame['timestamp_local'] < cutoff)
                & (frame['timestamp_local'] >= cutoff - pd.Timedelta(hours=24)),
                'demand_clean_mwh'
            ]
            self.assertEqual(len(history), 24)
            self.assertAlmostEqual(rows['history_mean_24h'].iloc[0], history.mean())
            for lag in (48, 168):
                source_times = features['timestamp_utc'].shift(lag).loc[rows.index]
                self.assertTrue((source_times < cutoff.tz_convert('UTC')).all())


class Week4PipelineTests(unittest.TestCase):
    """Integration checks against the actual generated feature dataset."""

    @classmethod
    def setUpClass(cls):
        path = Path('data/processed/ciso_day_ahead_features_2019_2025.csv')
        if not path.exists():
            raise AssertionError(
                'Feature dataset is missing. Run scripts/download_eia930_workbook.py '
                'and scripts/build_week4_analysis.py from the project root first.'
            )
        cls.df = pd.read_csv(path)

    def test_full_hourly_series(self):
        self.assertEqual(len(self.df), 61368)
        self.assertEqual(self.df['timestamp_utc'].nunique(), 61368)
        self.assertFalse(self.df['timestamp_utc'].duplicated().any())

    def test_target_is_valid(self):
        df = self.df
        self.assertEqual(df['raw_demand_mwh'].isna().sum(), 118)
        self.assertEqual(df['demand_clean_mwh'].isna().sum(), 0)
        self.assertTrue(np.isfinite(df['demand_clean_mwh']).all())
        self.assertGreater(df['demand_clean_mwh'].min(), 0)
        self.assertEqual(int(df['author_imputed'].sum()), 38)
        observed = df['target_observed'].eq(1)
        self.assertEqual(int(observed.sum()), 61236)
        self.assertTrue(df.loc[observed, 'raw_demand_mwh'].notna().all())
        self.assertTrue(df.loc[observed, 'source_range_error'].eq(0).all())
        self.assertTrue(df.loc[observed, 'isolated_discontinuity'].eq(0).all())

    def test_lag_values_and_cutoffs(self):
        df = self.df
        times = pd.to_datetime(df['timestamp_utc'], utc=True)
        cutoffs = pd.to_datetime(df['forecast_cutoff_local'], utc=True)
        for lag in (48, 168):
            values = df[f'demand_lag_{lag}h']
            np.testing.assert_allclose(
                values.iloc[lag:].to_numpy(),
                df['demand_clean_mwh'].iloc[:-lag].to_numpy(),
            )
            applicable = values.notna()
            self.assertTrue((times.shift(lag).loc[applicable] < cutoffs.loc[applicable]).all())

    def test_context_24h_means_and_cutoffs(self):
        df = self.df
        times = pd.to_datetime(df['timestamp_utc'], utc=True)
        cutoffs = pd.to_datetime(df['forecast_cutoff_local'], utc=True)
        for date in ('2024-03-11', '2024-11-04', '2024-06-15', '2025-09-01'):
            day = df['operating_date'].eq(date)
            self.assertTrue(day.any())
            cutoff = cutoffs.loc[day].iloc[0]
            local_cutoff = cutoff.tz_convert('America/Los_Angeles')
            self.assertEqual(local_cutoff.hour, 12)
            source = df.loc[(times < cutoff) & (times >= cutoff - pd.Timedelta(hours=24)), 'demand_clean_mwh']
            self.assertAlmostEqual(df.loc[day, 'history_mean_24h'].iloc[0], source.mean())

    def test_dst_day_lengths(self):
        lengths = self.df.groupby('operating_date').size()
        self.assertEqual(int(lengths.eq(23).sum()), 7)
        self.assertEqual(int(lengths.eq(25).sum()), 7)
        self.assertEqual(int((~lengths.isin([23, 24, 25])).sum()), 0)

    def test_feature_completeness(self):
        required = [
            'demand_lag_48h', 'demand_lag_168h',
            'history_mean_24h', 'history_std_24h',
            'history_min_24h', 'history_max_24h',
            'history_mean_168h', 'history_std_168h',
        ]
        complete = self.df[required].notna().all(axis=1)
        self.assertEqual(int(complete.sum()), 61200)
        self.assertFalse(complete.iloc[:168].any())
        self.assertTrue(complete.iloc[168:].all())

    def test_chronological_partitions(self):
        df = self.df
        train = df.loc[df['year'].between(2019, 2023), 'timestamp_utc']
        validation = df.loc[df['year'].eq(2024), 'timestamp_utc']
        test = df.loc[df['year'].eq(2025), 'timestamp_utc']
        self.assertLess(train.max(), validation.min())
        self.assertLess(validation.max(), test.min())
        self.assertEqual(len(test), 8760)


if __name__ == '__main__':
    unittest.main()
