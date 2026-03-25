"""Matplotlib chart builders for the Supply & Demand app."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from config import BAR_WIDTH_DAYS, CHART_FIGSIZE_TALL, CHART_FIGSIZE_WIDE


# ── Shared helpers ───────────────────────────────────────────────────────────

def get_region_backlog(backlog_df: pd.DataFrame, region_label: str) -> float:
    """Return the hour-backlog for a single region, or 0 if not found."""
    match = backlog_df.loc[backlog_df["Region"] == region_label, "HOUR_BACKLOG"]
    return float(match.iloc[0]) if not match.empty else 0.0


def _monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
    """Aggregate scenario results to monthly level and compute cumulative backlog."""
    if df.empty:
        return pd.DataFrame()

    agg_cols = [
        "BASE_SUPPLY",
        "SCENARIO_SUPPLY",
        "DEMAND",
        "BASE_GAP",
        "SCENARIO_GAP",
        "SUPPLY_DELTA",
    ]
    monthly = (
        df.groupby("DATE", as_index=False)[
            ["BASE_SUPPLY", "SCENARIO_SUPPLY", "DEMAND",
             "BASE_GAP", "SCENARIO_GAP", "SUPPLY_DELTA"]
        ]
        .sum()
        .sort_values("DATE")
        .assign(
            BASE_GAP_CUMSUM=lambda d: -pd.to_numeric(d["BASE_GAP"], errors="coerce").cumsum(),
            SCENARIO_GAP_CUMSUM=lambda d: (
                backlog + (-pd.to_numeric(d["SCENARIO_GAP"], errors="coerce")).cumsum()
            ),
        )
    )
    monthly["DATE"] = pd.to_datetime(monthly["DATE"])

    # Cumulative backlog: negate the gap so a deficit accumulates positively
    monthly["BASE_GAP_CUMSUM"] = (
        -pd.to_numeric(monthly["BASE_GAP"], errors="coerce").cumsum()
    )
    monthly["SCENARIO_GAP_CUMSUM"] = float(backlog) + (
        -pd.to_numeric(monthly["SCENARIO_GAP"], errors="coerce").cumsum()
    )
    monthly["BACKLOG_AS_SUPPLY"] = (
        monthly["SCENARIO_GAP_CUMSUM"] / monthly["SCENARIO_SUPPLY"]
    )
    return monthly


def _padded_limits(series: pd.Series, padding_frac: float = 0.2, min_pad: float = 1) -> tuple[float, float]:
    """Return (ymin, ymax) with symmetric padding around zero-inclusive bounds."""
    lo = min(series.min(), 0)
    hi = max(series.max(), 0)
    pad = max((hi - lo) * padding_frac, min_pad)
    return lo - pad, hi + pad


def _split_base_adjusted(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split monthly frame into base (no adjustment) and adjusted rows."""
    monthly["IS_ADJUSTED"] = monthly["SUPPLY_DELTA"] != 0
    monthly["DISPLAY_GAP"] = monthly["SCENARIO_GAP"].where(
        monthly["IS_ADJUSTED"], monthly["BASE_GAP"],
    )
    return monthly[~monthly["IS_ADJUSTED"]], monthly[monthly["IS_ADJUSTED"]]


# ── Baseline & scenario line charts ─────────────────────────────────────────

def _line_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
) -> Figure | None:
    """Line chart: scenario supply, demand, and gap over time."""
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    for col, label in [
        ("SCENARIO_SUPPLY", "Scenario Supply"),
        ("DEMAND", "Demand"),
        ("SCENARIO_GAP", "Scenario Gap"),
    ]:
        ax.plot(monthly["DATE"], monthly[col], marker="o", label=label)

    ax.set_title(f"Scenario Supply vs Demand vs Gap — {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return _finalize(fig)


def supply_delta_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0.0,
) -> Figure | None:
    """Gap bars + cumulative backlog line + normalized backlog line.

    Labels only at first / middle / last months to avoid clutter.
    Legend placed outside the plot area.
    """
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)
    key_idx = _key_label_indices(len(monthly))

    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    _draw_gap_bars(ax1, base_months, adjusted_months)
    _draw_backlog_line(
        ax2, monthly,
        label="Cumulative Backlog (hours)",
        annotate_all=False, annotate_indices=key_idx,
    )
    _draw_normalized_line(
        ax3, monthly,
        label="Normalized Backlog (Squad-Months)",
        annotate_all=False, annotate_indices=key_idx, fmt=".1f",
    )

    ax1.set_ylim(*_padded_limits(monthly["DISPLAY_GAP"]))
    ax2.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], 0.1))
    ax3.set_ylim(*_padded_limits(monthly["NORMALIZED_BACKLOG"], 0.1, 0.1))

    ax1.set_title(f"Backlog Summary — {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Supply vs Demand Gap (hours)")
    for twin in (ax2, ax3):
        twin.set_ylabel("")
        twin.set_yticks([])

    # Combined legend
    handles = sum((a.get_legend_handles_labels()[0] for a in (ax1, ax2, ax3)), [])
    labels = sum((a.get_legend_handles_labels()[1] for a in (ax1, ax2, ax3)), [])
    ax1.legend(handles, labels, loc=7, bbox_to_anchor=(1.3, 0.5), ncol=1)
    ax1.grid(True, axis="y", alpha=0.3)

    return _finalize(fig)


def supply_delta_chart2(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0.0,
) -> Figure | None:
    """Two-panel variant: gap bars (top) + cumulative backlog (bottom)."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=CHART_FIGSIZE_TALL, sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    _draw_gap_bars(ax_top, base_months, adjusted_months)
    ax_top.set_ylim(*_padded_limits(monthly["DISPLAY_GAP"]))
    ax_top.set_title(f"Monthly Gap and Backlog — {region_label}")
    ax_top.set_ylabel("Monthly Gap Hours")
    ax_top.legend()
    ax_top.grid(True, axis="y", alpha=0.3)

    _draw_backlog_line(ax_bot, monthly, annotate_all=True)
    ax_bot.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], 0.1))
    ax_bot.set_ylabel("Backlog Hours")
    ax_bot.set_xlabel("Month")
    ax_bot.legend()
    ax_bot.grid(True, axis="y", alpha=0.3)

    return _finalize(fig)


def supply_delta_chart3(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0.0,
) -> Figure | None:
    """Single-panel: gap bars + backlog + normalized backlog (all labels)."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)

    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    _draw_gap_bars(ax1, base_months, adjusted_months)
    _draw_backlog_line(ax2, monthly, annotate_all=True)
    _draw_normalized_line(ax3, monthly, annotate_all=True)

    ax1.set_ylim(*_padded_limits(monthly["DISPLAY_GAP"]))
    ax2.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], 0.1))
    ax3.set_ylim(*_padded_limits(monthly["NORMALIZED_BACKLOG"], 0.1, 0.1))

    ax1.set_title(f"Monthly Gap — {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Gap Hours")
    for twin in (ax2, ax3):
        twin.set_ylabel("")
        twin.set_yticks([])

    handles = sum((a.get_legend_handles_labels()[0] for a in (ax1, ax2, ax3)), [])
    labels = sum((a.get_legend_handles_labels()[1] for a in (ax1, ax2, ax3)), [])
    ax1.legend(handles, labels, loc="upper right")
    ax1.grid(True, axis="y", alpha=0.3)

    return _finalize(fig)


def supply_delta_chart4(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0.0,
) -> Figure | None:
    """Single-panel: gap bars + backlog + normalized (sparse labels)."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)
    key_idx = _key_label_indices(len(monthly))

    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    _draw_gap_bars(ax1, base_months, adjusted_months)
    _draw_backlog_line(
        ax2, monthly,
        label="Cumulative Backlog (hours)",
        annotate_all=False, annotate_indices=key_idx,
    )
    _draw_normalized_line(
        ax3, monthly,
        label="Normalized Backlog (Squad-Months)",
        annotate_all=False, annotate_indices=key_idx,
    )

    ax1.set_ylim(*_padded_limits(monthly["DISPLAY_GAP"]))
    ax2.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], 0.1))
    ax3.set_ylim(*_padded_limits(monthly["NORMALIZED_BACKLOG"], 0.1, 0.1))

    ax1.set_title(f"Backlog Summary — {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Supply vs Demand Gap (hours)")
    for twin in (ax2, ax3):
        twin.set_ylabel("")
        twin.set_yticks([])

    handles = sum((a.get_legend_handles_labels()[0] for a in (ax1, ax2, ax3)), [])
    labels = sum((a.get_legend_handles_labels()[1] for a in (ax1, ax2, ax3)), [])
    ax1.legend(handles, labels, loc=7, bbox_to_anchor=(1.3, 0.5), ncol=1)
    ax1.grid(True, axis="y", alpha=0.3)

    return _finalize(fig)
