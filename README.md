# USD ADS-599 Capstone — Group 1

Historical **day-ahead hourly electricity-demand forecasting** for the California Independent System Operator (CISO) balancing-authority footprint, using U.S. EIA Form EIA-930 published data for 2019–2025.

## Canonical Week 4 source and outputs

- `scripts/download_eia930_workbook.py`: downloads the published full-history CISO Excel workbook, the **canonical source** for Week 4.
- `scripts/build_week4_analysis.py`: creates auditable cleaned/feature CSVs, EDA summary, tables, and three publication figures.
- `tests/test_week4_pipeline.py`: independent DST/cutoff unit checks and integration checks against generated features.
- `USD_Capstone_Week_4_Draft_Group_1.docx`: manuscript draft (data understanding, EDA, preparation, and feature design).
- `outputs/week4/eda_summary.json`: recorded summary of the supplied baseline run; **regenerate it** when rerunning the analysis.

Generated paths include `data/raw/EIA930_CISO.xlsx`, `data/processed/ciso_hourly_demand_2019_2025.csv`, `data/processed/ciso_day_ahead_features_2019_2025.csv`, `outputs/week4/tables/`, and `outputs/week4/figures/`.

## Reproduce the analysis

Use Python 3.11+ and run from the **repository root**:

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_eia930_workbook.py
python scripts/build_week4_analysis.py
python -m unittest discover -s tests -v
```

The integration tests **fail, rather than silently skip**, if the generated feature CSV is missing. The separately runnable DST/noon-cutoff unit tests do not require downloaded EIA data. Plotting uses cross-platform font fallbacks.

For exact environment replay, record a tested `pip freeze` snapshot alongside your Python interpreter version after the full pipeline passes. The version ranges in `requirements.txt` are not an exact environment lock.

## Forecast-time design

The intended prediction batch contains all hours for the **next Pacific operating date**, with issuance at **12:00 p.m. Pacific on the preceding day**. Timezone-aware cutoff construction preserves noon across daylight-saving transitions. Baseline historical predictors include 48-hour and 168-hour hourly lags plus calendar and pre-issuance historical summary features. Audit and target-quality flags dependent on target outcomes **must not** be model predictors.

Planned evaluation periods: 2019–2023 development training, 2024 validation/tuning, 2025 untouched holdout. These boundaries are a plan; subsequent model-fitting code must enforce them. Current-source retrospective revisions may not reproduce precisely what was available at historical issuance.

## Optional EIA API comparison

`scripts/download_eia930.py` provides an optional newline-delimited JSON API extraction. **It is not used for the Week 4 reported dataset.** EIA API `period` fields and workbook UTC hour-ending fields may not share the same interpretation. Reconcile their hourly timestamp conventions and coverage before substituting API data; do not silently treat the two files as identical.

## Data-quality conventions

The canonical pipeline keeps all UTC hourly positions and preserves raw, EIA-imputed, adjusted, cleaned, and quality-flag fields. The author's 60%-of-both-neighbors downward-discontinuity test is a **heuristic**, not a validated industry rule. Its effect should be sensitivity-tested against retaining original flagged values in a later model-evaluation milestone. Exclude missing or anomalous raw target observations from supervised evaluation, even when a continuity-filled value exists for history features.
