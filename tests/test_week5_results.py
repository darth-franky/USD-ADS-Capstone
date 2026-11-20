"""Independent checks of the exported model protocol and prediction metrics."""
from pathlib import Path
import hashlib
import json
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/week5'


class Week5ResultsTests(unittest.TestCase):
    def test_source_and_predictors(self):
        protocol = json.loads((OUT / 'protocol.json').read_text())
        source = ROOT / 'data/processed/ciso_day_ahead_features_2019_2025.csv'
        self.assertEqual(protocol['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        forbidden = {'target', 'raw_demand_mwh', 'published_demand_mwh', 'demand_clean_mwh',
                     'eia_demand_forecast_mwh', 'target_observed', 'author_imputed'}
        self.assertFalse(forbidden.intersection(protocol['features']))

    def test_selection_is_validation_based(self):
        cv = pd.read_csv(OUT / 'validation_scores.csv')
        selection = json.loads((OUT / 'selection.json').read_text())
        self.assertEqual(set(cv.year), {2022, 2023, 2024})
        for model, config in selection['selected_configs'].items():
            self.assertEqual(config, int(cv[cv.model.eq(model)].groupby('config').mae.mean().idxmin()))
        self.assertEqual(selection['selected_model'], min(selection['validation_mean_mae'], key=selection['validation_mean_mae'].get))

    def test_exported_errors_recompute(self):
        predictions = pd.read_csv(OUT / 'test_predictions.csv')
        scores = pd.read_csv(OUT / 'model_scores.csv')
        self.assertEqual(len(predictions), 8760)
        self.assertEqual(predictions.utc_time.nunique(), 8760)
        self.assertTrue(pd.to_datetime(predictions.operating_date).dt.year.eq(2025).all())
        for row in scores[scores.partition.eq('Test 2025')].itertuples():
            error = predictions[row.model] - predictions.target
            self.assertTrue(np.isfinite(predictions[row.model]).all())
            self.assertAlmostEqual(error.abs().mean(), row.mae, places=8)
            self.assertAlmostEqual(np.sqrt((error ** 2).mean()), row.rmse, places=8)
            self.assertEqual(error.notna().sum(), row.n)

    def test_peak_days_include_dst_and_exclude_missing_targets(self):
        predictions = pd.read_csv(OUT / 'test_predictions.csv')
        daily = pd.read_csv(OUT / 'daily_peak_scores.csv')
        counts = predictions.groupby('operating_date').target.agg(['size', 'count'])
        self.assertEqual(set(counts['size']), {23, 24, 25})
        eligible = set(counts.index[counts['size'].eq(counts['count'])])
        for _, rows in daily.groupby('model'):
            self.assertEqual(set(rows.date), eligible)
        folds = pd.read_csv(OUT / 'folds.csv')
        self.assertTrue((pd.to_datetime(folds.train_end).dt.year < folds.year).all())


if __name__ == '__main__':
    unittest.main()
