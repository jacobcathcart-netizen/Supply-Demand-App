"""Monthly aggregation helpers extracted from components.visuals.

These are pure pandas functions with no Streamlit dependency, shared
by both the chart builders and the sensitivity engine.
"""

from __future__ import annotations

import pandas as pd


def monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
    """Aggregate scenario results to monthly level and compute cumulative backlog."""
    if df.empty:
        return pd.DataFrame()

    backlog = float(backlog)

    agg_cols = [
        "BASE_SUPPLY",
        "SCENARIO_SUPPLY",
        "DEMAND",
        "BASE_GAP",
        "SCENARIO_GAP",
        "SUPPLY_DELTA",
    ]
    if "SCENARIO_DEMAND" in df.columns:
        agg_cols.insert(3, "SCENARIO_DEMAND")

    monthly = (
        df.groupby("DATE", as_index=False)[agg_cols]
        .sum()
        .sort_values("DATE")
    )
    monthly["DATE"] = pd.to_datetime(monthly["DATE"])

    base_gap = pd.to_numeric(monthly["BASE_GAP"], errors="coerce")
    scen_gap = pd.to_numeric(monthly["SCENARIO_GAP"], errors="coerce")

    base_cumsum = []
    scen_cumsum = []
    prev_base = 0.0
    prev_scen = backlog
    for b, s in zip(base_gap, scen_gap):
        prev_base = max(prev_base - b, 0.0)
        prev_scen = max(prev_scen - s, 0.0)
        base_cumsum.append(prev_base)
        scen_cumsum.append(prev_scen)

    monthly["BASE_GAP_CUMSUM"] = base_cumsum
    monthly["SCENARIO_GAP_CUMSUM"] = scen_cumsum
    monthly["BACKLOG_AS_SUPPLY"] = (
        monthly["SCENARIO_GAP_CUMSUM"]
        / monthly["SCENARIO_SUPPLY"].replace(0, float("nan"))
    )
    return monthly


def padded_limits(
    series: pd.Series,
    padding_frac: float = 0.2,
    min_pad: float = 1,
) -> tuple[float, float]:
    """Return (ymin, ymax) with symmetric padding around zero-inclusive bounds."""
    lo = min(series.min(), 0)
    hi = max(series.max(), 0)
    pad = max((hi - lo) * padding_frac, min_pad)
    return lo - pad, hi + pad


def split_base_adjusted(
    monthly_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split monthly frame into base (no adjustment) and adjusted rows."""
    is_adjusted = monthly_df["SUPPLY_DELTA"] != 0
    display_gap = monthly_df["SCENARIO_GAP"].where(is_adjusted, monthly_df["BASE_GAP"])
    m = monthly_df.assign(IS_ADJUSTED=is_adjusted, DISPLAY_GAP=display_gap)
    return m[~m["IS_ADJUSTED"]], m[m["IS_ADJUSTED"]]
