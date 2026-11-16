#!/usr/bin/env python3
"""Audit, prepare, feature-engineer, and visualize the Week 4 CISO data."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from PIL import Image, ImageDraw, ImageFont


RAW_PATH = Path("data/raw/EIA930_CISO.xlsx")
PROCESSED_PATH = Path("data/processed/ciso_hourly_demand_2019_2025.csv")
FEATURE_PATH = Path("data/processed/ciso_day_ahead_features_2019_2025.csv")
OUTPUT_DIR = Path("outputs/week4")
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

BLUE = "#0B4F8A"
NAVY = "#16324F"
ORANGE = "#E07A3F"
TEAL = "#2A9D8F"
GRAY = "#667085"
LIGHT_GRID = "#D9E2EC"
TEXT = "#1F2933"
WHITE = "#FFFFFF"
SEASON_COLORS = {
    "Winter": "#3C78B5",
    "Spring": "#46A67A",
    "Summer": "#D9793D",
    "Fall": "#8B62A3",
}


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load an available font on Windows, macOS, or Linux."""
    candidates = (
        ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]
        if bold else
        ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Older Pillow versions
        return ImageFont.load_default()


def load_data() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Run scripts/download_eia930_workbook.py first: {RAW_PATH}")
    columns = [
        "BA", "UTC time", "Local date", "Hour", "Local time", "Time zone",
        "Demand forecast", "Demand", "Imputed demand", "Adjusted demand",
    ]
    df = pd.read_excel(RAW_PATH, sheet_name="Published Hourly Data", usecols=columns)
    df = df[(df["Local date"] >= "2019-01-01") & (df["Local date"] <= "2025-12-31")].copy()
    df = df.rename(
        columns={
            "BA": "respondent",
            "UTC time": "timestamp_utc",
            "Local date": "local_date",
            "Hour": "hour_ending",
            "Local time": "local_time_reported",
            "Time zone": "time_zone",
            "Demand forecast": "eia_demand_forecast_mwh",
            "Demand": "raw_demand_mwh",
            "Imputed demand": "eia_imputed_demand_mwh",
            "Adjusted demand": "published_demand_mwh",
        }
    )
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert("America/Los_Angeles")
    df["local_date"] = pd.to_datetime(df["local_date"])
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    thresholds = pd.read_excel(RAW_PATH, sheet_name="Range Thresholds")
    demand_threshold = thresholds.loc[
        thresholds["Threshold Description"] == "Acceptable demand range"
    ].iloc[0]
    lower = float(demand_threshold["Lower Threshold"])
    upper = float(demand_threshold["Upper Threshold"])
    df["source_range_error"] = (
        df["published_demand_mwh"].notna()
        & ~df["published_demand_mwh"].between(lower, upper)
    ).astype(int)
    previous = df["published_demand_mwh"].shift(1)
    following = df["published_demand_mwh"].shift(-1)
    df["isolated_discontinuity"] = (
        (df["published_demand_mwh"] < 0.60 * previous)
        & (df["published_demand_mwh"] < 0.60 * following)
    ).astype(int)
    df["author_imputed"] = (
        df["published_demand_mwh"].isna()
        | df["source_range_error"].eq(1)
        | df["isolated_discontinuity"].eq(1)
    ).astype(int)
    usable = df["published_demand_mwh"].mask(
        df["source_range_error"].eq(1) | df["isolated_discontinuity"].eq(1)
    )
    # The previous-week replacement is a historical continuity treatment.
    # Data are retrospective and may contain EIA revisions unavailable at the
    # original forecast issuance. Preserve observation flags for evaluation.
    df["demand_clean_mwh"] = usable.fillna(usable.shift(168)).ffill()
    df["target_observed"] = (
        df["raw_demand_mwh"].notna()
        & df["source_range_error"].eq(0)
        & df["isolated_discontinuity"].eq(0)
    ).astype(int)
    return df


def add_calendar_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    operating = out["local_date"]
    out["operating_date"] = operating.dt.date.astype(str)
    out["year"] = operating.dt.year
    out["month"] = operating.dt.month
    out["day_of_week"] = operating.dt.dayofweek
    out["hour_local"] = out["timestamp_local"].dt.hour
    out["day_of_year"] = operating.dt.dayofyear
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    calendar = USFederalHolidayCalendar()
    holidays = calendar.holidays(start="2018-12-01", end="2026-01-31").date
    out["is_federal_holiday"] = operating.dt.date.isin(holidays).astype(int)
    out["hour_sin"] = np.sin(2 * np.pi * out["hour_local"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour_local"] / 24)
    out["dow_sin"] = np.sin(2 * np.pi * out["day_of_week"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["day_of_week"] / 7)
    out["doy_sin"] = np.sin(2 * np.pi * out["day_of_year"] / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * out["day_of_year"] / 365.25)
    return out


def add_leakage_safe_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["demand_lag_48h"] = out["demand_clean_mwh"].shift(48)
    out["demand_lag_168h"] = out["demand_clean_mwh"].shift(168)

    # Each target operating day uses a noon Pacific cutoff on the prior day.
    indexed = out.set_index("timestamp_local")["demand_clean_mwh"]
    daily_rows: list[dict] = []
    for operating_date in pd.to_datetime(out["operating_date"].unique()):
        # Localize the wall-clock noon directly. Adding 12 elapsed hours to
        # localized midnight is incorrect on the preceding day's DST switch.
        prior_day_noon = operating_date - pd.Timedelta(days=1) + pd.Timedelta(hours=12)
        cutoff = prior_day_noon.tz_localize("America/Los_Angeles")
        history_24 = indexed[(indexed.index < cutoff) & (indexed.index >= cutoff - pd.Timedelta(hours=24))]
        history_168 = indexed[(indexed.index < cutoff) & (indexed.index >= cutoff - pd.Timedelta(hours=168))]
        daily_rows.append(
            {
                "operating_date": operating_date.date().isoformat(),
                "forecast_cutoff_local": cutoff.isoformat(),
                "history_mean_24h": history_24.mean(),
                "history_std_24h": history_24.std(ddof=0),
                "history_min_24h": history_24.min(),
                "history_max_24h": history_24.max(),
                "history_mean_168h": history_168.mean(),
                "history_std_168h": history_168.std(ddof=0),
                "history_observations_24h": len(history_24),
                "history_observations_168h": len(history_168),
            }
        )
    context = pd.DataFrame(daily_rows)
    return out.merge(context, on="operating_date", how="left", validate="many_to_one")


def data_quality_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    expected = pd.date_range(
        "2019-01-01T09:00:00Z", "2026-01-01T08:00:00Z", freq="h"
    )
    missing_timestamps = len(expected.difference(pd.DatetimeIndex(df["timestamp_utc"])))
    duplicate_timestamps = int(df["timestamp_utc"].duplicated().sum())
    raw_missing = int(df["raw_demand_mwh"].isna().sum())
    eia_imputed = int(df["eia_imputed_demand_mwh"].notna().sum())
    remaining_missing = int(df["published_demand_mwh"].isna().sum())
    range_errors = int(df["source_range_error"].sum())
    discontinuities = int(df["isolated_discontinuity"].sum())
    author_imputed = int(df["author_imputed"].sum())
    nonpositive = int((df["published_demand_mwh"].dropna() <= 0).sum())

    q1 = float(df["demand_clean_mwh"].quantile(0.25))
    q3 = float(df["demand_clean_mwh"].quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    iqr_flags = int(((df["demand_clean_mwh"] < lower) | (df["demand_clean_mwh"] > upper)).sum())

    local_day_counts = df.groupby("operating_date").size()
    count_23 = int((local_day_counts == 23).sum())
    count_24 = int((local_day_counts == 24).sum())
    count_25 = int((local_day_counts == 25).sum())
    other_day_counts = int((~local_day_counts.isin([23, 24, 25])).sum())

    rows = [
        ("Expected UTC hours", len(expected), "Complete Pacific calendar years 2019–2025"),
        ("Published hourly rows", len(df), "All expected CISO hourly identifiers in 2019–2025"),
        ("Missing UTC timestamps", missing_timestamps, "Expected hourly identifiers absent from the workbook"),
        ("Duplicate UTC timestamps", duplicate_timestamps, "Repeated unique hourly identifiers"),
        ("Missing raw demand", raw_missing, "Raw reported demand is null"),
        ("EIA-imputed demand", eia_imputed, "Missing raw demand filled by EIA"),
        ("Missing after EIA adjustment", remaining_missing, "Published adjusted demand remains null"),
        ("EIA range errors", range_errors, "Published demand outside the 10,000–70,877 MWh CISO range"),
        ("Isolated discontinuities", discontinuities, "Values below 60% of both adjacent hours"),
        ("Author continuity fills", author_imputed, "Missing or anomalous hours replaced with the 168-hour lag"),
        ("Nonpositive demand values", nonpositive, "Values at or below zero"),
        ("IQR flags", iqr_flags, "Values outside 1.5 × IQR; reviewed, not automatically removed"),
        ("23-hour local days", count_23, "Spring daylight-saving transitions"),
        ("24-hour local days", count_24, "Standard operating days"),
        ("25-hour local days", count_25, "Fall daylight-saving transitions"),
        ("Other local-day lengths", other_day_counts, "Possible missing or duplicated local-day observations"),
    ]
    table = pd.DataFrame(rows, columns=["check", "count", "interpretation"])
    summary = {
        "expected_hours": len(expected),
        "published_rows": len(df),
        "missing_timestamps": missing_timestamps,
        "duplicate_timestamps": duplicate_timestamps,
        "raw_missing_demand_values": raw_missing,
        "raw_missing_demand_percent": 100 * raw_missing / len(df),
        "eia_imputed_demand_values": eia_imputed,
        "eia_imputed_demand_percent": 100 * eia_imputed / len(df),
        "remaining_missing_after_eia": remaining_missing,
        "remaining_missing_after_eia_percent": 100 * remaining_missing / len(df),
        "source_range_errors": range_errors,
        "source_range_error_percent": 100 * range_errors / len(df),
        "isolated_discontinuities": discontinuities,
        "isolated_discontinuity_percent": 100 * discontinuities / len(df),
        "author_continuity_fills": author_imputed,
        "author_continuity_fill_percent": 100 * author_imputed / len(df),
        "valid_observed_targets": int(df["target_observed"].sum()),
        "nonpositive_demand_values": nonpositive,
        "iqr_lower_bound_mwh": lower,
        "iqr_upper_bound_mwh": upper,
        "iqr_flagged_rows": iqr_flags,
        "iqr_flagged_percent": 100 * iqr_flags / len(df),
        "local_days_23_hours": count_23,
        "local_days_24_hours": count_24,
        "local_days_25_hours": count_25,
        "local_days_other_lengths": other_day_counts,
    }
    return table, summary


def profile_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    annual = (
        df.groupby("year")["demand_clean_mwh"]
        .agg(observations="count", mean_mwh="mean", median_mwh="median", min_mwh="min", max_mwh="max")
        .reset_index()
    )
    monthly = (
        df.groupby("month")["demand_clean_mwh"]
        .agg(mean_mwh="mean", median_mwh="median", max_mwh="max")
        .reset_index()
    )
    hourly = (
        df.groupby("hour_local")["demand_clean_mwh"]
        .agg(mean_mwh="mean", median_mwh="median", max_mwh="max")
        .reset_index()
    )
    autocorrelation = pd.DataFrame(
        {
            "lag_hours": [1, 24, 48, 168],
            "correlation": [df["demand_clean_mwh"].autocorr(lag=lag) for lag in [1, 24, 48, 168]],
        }
    )
    return {
        "annual_summary": annual,
        "monthly_profile": monthly,
        "hourly_profile": hourly,
        "autocorrelation": autocorrelation,
    }


def canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1600, 960), WHITE)
    draw = ImageDraw.Draw(image)
    draw.text((95, 55), title, fill=NAVY, font=font(48, True))
    if subtitle:
        draw.text((95, 115), subtitle, fill=GRAY, font=font(25))
    return image, draw


def axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], y_ticks: Iterable[float], y_min: float, y_max: float) -> None:
    x0, y0, x1, y1 = box
    draw.line((x0, y1, x1, y1), fill=TEXT, width=2)
    draw.line((x0, y0, x0, y1), fill=TEXT, width=2)
    for value in y_ticks:
        y = y1 - (value - y_min) / (y_max - y_min) * (y1 - y0)
        draw.line((x0, y, x1, y), fill=LIGHT_GRID, width=2)
        label = f"{value/1000:.0f}k"
        draw.text((x0 - 75, y - 13), label, fill=GRAY, font=font(22))


def map_xy(index: float, value: float, n: int, box: tuple[int, int, int, int], y_min: float, y_max: float) -> tuple[float, float]:
    x0, y0, x1, y1 = box
    x = x0 + index / max(1, n - 1) * (x1 - x0)
    y = y1 - (value - y_min) / (y_max - y_min) * (y1 - y0)
    return x, y


def figure_daily_trend(df: pd.DataFrame, path: Path) -> None:
    daily = df.groupby("operating_date")["demand_clean_mwh"].agg(["mean", "max"]).reset_index()
    daily["date"] = pd.to_datetime(daily["operating_date"])
    smooth = daily["mean"].rolling(30, center=True, min_periods=1).mean()
    image, draw = canvas(
        "CISO Demand Shows Seasonal Peaks and Year-to-Year Variation",
        "Daily maximum and 30-day mean, Pacific operating dates, 2019–2025",
    )
    box = (150, 205, 1510, 815)
    y_min, y_max = 10000, 55000
    axes(draw, box, np.arange(10000, 55001, 10000), y_min, y_max)
    max_points = [map_xy(i, v, len(daily), box, y_min, y_max) for i, v in enumerate(daily["max"])]
    smooth_points = [map_xy(i, v, len(daily), box, y_min, y_max) for i, v in enumerate(smooth)]
    draw.line(max_points, fill="#B7C6D4", width=2)
    draw.line(smooth_points, fill=BLUE, width=5)
    start = daily["date"].min()
    end = daily["date"].max()
    span = (end - start).days
    for year in range(2019, 2026):
        pos = (pd.Timestamp(f"{year}-07-01") - start).days / span
        x = box[0] + pos * (box[2] - box[0])
        draw.text((x - 28, box[3] + 24), str(year), fill=GRAY, font=font(22))
    draw.text((150, 170), "Demand (MWh)", fill=TEXT, font=font(25), anchor="ls")
    draw.line((1040, 155, 1100, 155), fill=BLUE, width=5)
    draw.text((1115, 141), "30-day mean", fill=TEXT, font=font(22))
    draw.line((1280, 155, 1340, 155), fill="#B7C6D4", width=4)
    draw.text((1355, 141), "Daily maximum", fill=TEXT, font=font(22))
    draw.text((95, 905), "Source: U.S. Energy Information Administration Form EIA-930; authors’ calculations.", fill=GRAY, font=font(20))
    image.save(path, quality=95)


def season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Fall"


def figure_seasonal_profiles(df: pd.DataFrame, path: Path) -> None:
    work = df.copy()
    work["season"] = work["month"].map(season_for_month)
    profile = work.groupby(["season", "hour_local"])["demand_clean_mwh"].mean().unstack(0)
    image, draw = canvas(
        "The Average Daily Load Shape Changes by Season",
        "Mean hourly CISO demand by Pacific local clock hour, 2019–2025",
    )
    box = (150, 205, 1510, 815)
    y_min = math.floor(profile.min().min() / 5000) * 5000
    y_max = math.ceil(profile.max().max() / 5000) * 5000
    axes(draw, box, np.arange(y_min, y_max + 1, 5000), y_min, y_max)
    for hour in range(0, 24, 3):
        x = box[0] + hour / 23 * (box[2] - box[0])
        draw.text((x - 15, box[3] + 24), f"{hour:02d}", fill=GRAY, font=font(22))
    for season in ["Winter", "Spring", "Summer", "Fall"]:
        values = profile[season].reindex(range(24))
        points = [map_xy(i, v, 24, box, y_min, y_max) for i, v in enumerate(values)]
        draw.line(points, fill=SEASON_COLORS[season], width=6)
    draw.text((150, 170), "Demand (MWh)", fill=TEXT, font=font(25), anchor="ls")
    draw.text((775, 865), "Pacific local hour ending", fill=TEXT, font=font(25), anchor="mm")
    x = 950
    for season in ["Winter", "Spring", "Summer", "Fall"]:
        draw.line((x, 155, x + 45, 155), fill=SEASON_COLORS[season], width=6)
        draw.text((x + 55, 141), season, fill=TEXT, font=font(22))
        x += 150
    draw.text((95, 905), "Source: U.S. Energy Information Administration Form EIA-930; authors’ calculations.", fill=GRAY, font=font(20))
    image.save(path, quality=95)


def heat_color(value: float, low: float, high: float) -> str:
    t = 0.0 if high == low else (value - low) / (high - low)
    stops = [(235, 244, 250), (91, 155, 213), (12, 73, 121)]
    if t < 0.5:
        a, b, u = stops[0], stops[1], t * 2
    else:
        a, b, u = stops[1], stops[2], (t - 0.5) * 2
    rgb = tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return "#%02x%02x%02x" % rgb


def figure_heatmap(df: pd.DataFrame, path: Path) -> None:
    pivot = df.pivot_table(index="month", columns="hour_local", values="demand_clean_mwh", aggfunc="mean").reindex(index=range(1, 13), columns=range(24))
    image, draw = canvas(
        "Demand Is Highest During Summer Afternoons and Evenings",
        "Mean CISO demand by month and Pacific local clock hour, 2019–2025",
    )
    x0, y0 = 220, 205
    cell_w, cell_h = 52, 48
    low, high = float(pivot.min().min()), float(pivot.max().max())
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for month in range(1, 13):
        draw.text((145, y0 + (month - 1) * cell_h + 10), month_names[month - 1], fill=TEXT, font=font(22))
        for hour in range(24):
            value = float(pivot.loc[month, hour])
            left = x0 + hour * cell_w
            top = y0 + (month - 1) * cell_h
            draw.rectangle((left, top, left + cell_w - 2, top + cell_h - 2), fill=heat_color(value, low, high))
    for hour in range(0, 24, 2):
        draw.text((x0 + hour * cell_w + 8, y0 + 12 * cell_h + 18), f"{hour:02d}", fill=GRAY, font=font(20))
    draw.text((845, 845), "Pacific local hour ending", fill=TEXT, font=font(25), anchor="mm")
    legend_x, legend_y = 1220, 855
    for i in range(120):
        t = i / 119
        draw.rectangle((legend_x + i * 2, legend_y, legend_x + i * 2 + 2, legend_y + 22), fill=heat_color(low + t * (high - low), low, high))
    draw.text((legend_x - 55, legend_y), f"{low/1000:.0f}k", fill=GRAY, font=font(18))
    draw.text((legend_x + 250, legend_y), f"{high/1000:.0f}k MWh", fill=GRAY, font=font(18))
    draw.text((95, 915), "Source: U.S. Energy Information Administration Form EIA-930; authors’ calculations.", fill=GRAY, font=font(20))
    image.save(path, quality=95)


def write_outputs(df: pd.DataFrame, quality_table: pd.DataFrame, summary: dict) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)

    clean_columns = [
        "timestamp_utc", "timestamp_local", "operating_date", "hour_ending",
        "raw_demand_mwh", "eia_imputed_demand_mwh", "published_demand_mwh",
        "demand_clean_mwh", "eia_demand_forecast_mwh", "target_observed",
        "source_range_error", "isolated_discontinuity", "author_imputed", "year", "month",
        "day_of_week", "hour_local", "day_of_year", "is_weekend", "is_federal_holiday",
    ]
    df[clean_columns].to_csv(PROCESSED_PATH, index=False)

    feature_columns = clean_columns + [
        "hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos",
        "demand_lag_48h", "demand_lag_168h", "forecast_cutoff_local",
        "history_mean_24h", "history_std_24h", "history_min_24h", "history_max_24h",
        "history_mean_168h", "history_std_168h", "history_observations_24h",
        "history_observations_168h",
    ]
    df[feature_columns].to_csv(FEATURE_PATH, index=False)

    quality_table.to_csv(TABLE_DIR / "data_quality_audit.csv", index=False)
    profiles = profile_tables(df)
    for name, table in profiles.items():
        table.to_csv(TABLE_DIR / f"{name}.csv", index=False)

    summary.update(
        {
            "period_start_local": str(df["timestamp_local"].min()),
            "period_end_local": str(df["timestamp_local"].max()),
            "mean_demand_mwh": float(df["demand_clean_mwh"].mean()),
            "median_demand_mwh": float(df["demand_clean_mwh"].median()),
            "minimum_demand_mwh": float(df["demand_clean_mwh"].min()),
            "maximum_demand_mwh": float(df["demand_clean_mwh"].max()),
            "standard_deviation_mwh": float(df["demand_clean_mwh"].std()),
            "autocorrelation_24h": float(df["demand_clean_mwh"].autocorr(lag=24)),
            "autocorrelation_48h": float(df["demand_clean_mwh"].autocorr(lag=48)),
            "autocorrelation_168h": float(df["demand_clean_mwh"].autocorr(lag=168)),
            "feature_rows_complete": int(df[["demand_lag_48h", "demand_lag_168h", "history_mean_168h"]].dropna().shape[0]),
        }
    )
    (OUTPUT_DIR / "eda_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    figure_daily_trend(df, FIGURE_DIR / "figure_1_daily_demand.png")
    figure_seasonal_profiles(df, FIGURE_DIR / "figure_2_seasonal_hourly_profiles.png")
    figure_heatmap(df, FIGURE_DIR / "figure_3_month_hour_heatmap.png")


def validate(df: pd.DataFrame) -> None:
    assert len(df) == 61368, f"Expected 61,368 rows, received {len(df):,}"
    assert df["timestamp_utc"].is_monotonic_increasing
    assert not df["timestamp_utc"].duplicated().any()
    assert df["year"].min() == 2019
    assert df["year"].max() == 2025
    assert set(df["respondent"]) == {"CISO"}
    assert not df["demand_clean_mwh"].isna().any()


def main() -> None:
    raw = load_data()
    prepared = add_calendar_fields(raw)
    validate(prepared)
    featured = add_leakage_safe_features(prepared)
    quality_table, summary = data_quality_summary(featured)
    write_outputs(featured, quality_table, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

