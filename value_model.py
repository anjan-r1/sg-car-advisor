# value_model.py

import pandas as pd
import numpy as np


def _normalize(series, reverse=False):
    """
    Normalize a numeric pandas series to range [0,1].
    For reverse=True: lower is better → we invert.
    """
    s = series.copy()
    s = s.replace([np.inf, -np.inf], np.nan)
    if s.isna().all():
        return pd.Series([0.5] * len(s))  # neutral score

    min_v = s.min()
    max_v = s.max()

    if max_v == min_v:
        # avoid divide by zero → constant series
        return pd.Series([0.5] * len(s))

    norm = (s - min_v) / (max_v - min_v)
    if reverse:
        norm = 1 - norm  # lower mileage/price = better
    return norm


def compute_value_scores(df):
    """
    Compute a composite 'value_score' for each row in df.
    A higher score = better relative value.

    Uses:
      - price_sgd (lower is better)
      - mileage_km (lower is better)
      - depreciation_per_year (lower is better)
      - year (newer is better)

    Returns:
      df with new columns:
         - value_price
         - value_mileage
         - value_depreciation
         - value_year
         - value_score
         - value_rank
    """

    df = df.copy()

    # Ensure numeric
    numeric_cols = ["price_sgd", "mileage_km", "depreciation_per_year", "year"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    # Normalized scores
    df["value_price"] = _normalize(df["price_sgd"], reverse=True)
    df["value_mileage"] = _normalize(df["mileage_km"], reverse=True)
    df["value_depreciation"] = _normalize(df["depreciation_per_year"], reverse=True)
    df["value_year"] = _normalize(df["year"], reverse=False)  # newer cars score higher

    # Composite score (weights can be tuned)
    df["value_score"] = (
        0.40 * df["value_price"] +
        0.25 * df["value_mileage"] +
        0.20 * df["value_depreciation"] +
        0.15 * df["value_year"]
    ) * 100  # scale to 0–100

    # Rank (1 = best)
    df["value_rank"] = df["value_score"].rank(ascending=False, method="dense")

    return df
