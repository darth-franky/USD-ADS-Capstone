# USD ADS Capstone

This project develops a reproducible, historical day-ahead electricity-demand forecasting workflow for the California Independent System Operator (CISO) balancing-authority footprint. The Week 4 work audits and prepares hourly U.S. Energy Information Administration Form EIA-930 demand data for 2019–2025, then creates leakage-aware features for later model comparison.

## Week 4 deliverables

- `USD_Capstone_Week_4_Draft_Group_1.docx`: article draft with the Data Summary, Exploratory Data Analysis, Data Preparation, and Feature Engineering sections.
- `scripts/download_eia930_workbook.py`: downloads the official CISO full-history workbook.
- `scripts/build_week4_analysis.py`: validates timestamps, applies documented continuity rules, engineers day-ahead features, and produces article-ready tables and figures.
- `outputs/week4/eda_summary.json`: machine-readable audit and EDA statistics.
- `outputs/week4/figures/`: the three figures included in the Week 4 draft.
- `data/raw/EIA930_CISO.xlsx`: the official CISO full-history workbook used for the milestone.
- `data/processed/`: cleaned hourly demand and feature tables used to reproduce the reported results.

## Reproduce the analysis

Create an environment and install the dependencies in `requirements.txt`, then run:

```bash
python3 scripts/download_eia930_workbook.py
python3 scripts/build_week4_analysis.py
python3 -m unittest discover -s tests -v
```

The canonical raw workbook and generated Week 4 CSV files are versioned so every teammate can reproduce the same results. The analysis preserves raw, EIA-imputed, published, and author-cleaned demand fields separately so every treatment remains auditable.

## Forecast boundary

The modeling design assumes that the next operating day's 24 hourly values are issued at 12:00 p.m. Pacific on the preceding day. Features must be available at that cutoff. Consequently, the initial feature set uses 48-hour and 168-hour demand lags rather than a potentially leaky 24-hour lag. The planned chronological split uses 2019–2023 for training, 2024 for validation and tuning, and 2025 as the final holdout.
