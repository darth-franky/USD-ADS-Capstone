# Week 5 modeling and evaluation handoff

Nikita's requested first draft is based on the current main-branch Week 4 dataset, not the alternate working-master analysis. The cumulative article preserves the Week 4 material, colors new Week 5 prose blue, and adds the modeling/evaluation sections, a pipeline diagram, and colored result tables. Team review is still required before the designated submitter uploads the PDF to Canvas.

## Reproduce

```bash
python -m pip install -r requirements-modeling.txt
python scripts/build_week5_models.py
python scripts/check_week5_sensitivity.py
python -m unittest discover -s tests -v
python scripts/build_week5_article.py
streamlit run app.py
```

The checked-in CSV and JSON results are enough to run the historical explorer. Trained joblib files are intentionally excluded from Git; regenerate them with the model script. Run the article builder in a Python environment containing python-docx and matplotlib. Export the resulting Word document to PDF for Canvas.

## Results

The validation-selected random forest has 2025 hourly MAE 1,066.1 MWh, versus 1,567.4 for weekly naive (32.0% reduction). Boosting is slightly better on 2025 hourly MAE, while ridge is better on peak magnitude. Selection remains based on 2022–2024. There are 8,711 eligible hourly targets and 362 complete assessment days.

## Decisions for Franky and Jun

- Review the no-reporting-delay assumption. The pipeline follows the merged Week 4 noon cutoff and 48/168-hour lags. It does not use the older alternate package's 24-hour reporting delay and 72/168/336-hour lags; its scores are therefore not directly comparable.
- Validate the anomaly rule scientifically. The isolated-discontinuity filter excludes 12 values and uses the following hour. Neighbors used for historical features are at or before issuance, but retrospective target-quality filtering may still affect which difficult cases are scored. A frozen-prediction scoring check retains the one additional flagged 2025 target: forest MAE changes from 1,066.1 to 1,068.3 MWh. Retraining on unfiltered histories remains future work.
- Review the annual expanding-window protocol. It adds 2022 and 2023 validation folds to the originally proposed 2024 validation year and purges labels beyond the first forecast cutoff.
- Do not describe 2025 as an untouched holdout: the Week 4 EDA and earlier alternate modeling already examined it. This run is a fixed-protocol replication. A genuinely later prospective period is required for an unbiased operational assessment.
- Reconcile the cumulative article against the latest team manuscript. The repository contains Week 4 Draft 2; this update carries forward the metric rationale and literature-review opening from the later Draft 3. Remaining wording, reference spacing, and acknowledgments need the authors’ final comparison.
- Read the explicit AI acknowledgment and verify the arguments and code before submission. Thirteen automated checks passed; author review is separate.

## Tool scope

The Streamlit application is a historical forecast explorer with daily curves, peak metrics, full-year results, and CSV export. It does not fetch current data or issue live forecasts. It is useful for the final tool artifact but still requires rubric review, deployment, and a team-approved demonstration.

## Submission status

This is a team-review draft, not a Canvas submission. Week 5 is due November 23, 2026. The discussion section, final article, final presentation, writing-center feedback, and final tool have separate requirements and are not automatically complete because this package exists.
