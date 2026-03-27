"""Matplotlib chart builders for the Supply & Demand app.

All charts use the CCR brand palette and a clean, enterprise aesthetic.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.figure import Figure

from components.branding import (
    GOLD,
    GRAY_200,
    GRAY_600,
    LIGHT_BLUE,
    NAVY,
    ORANGE,
    TEAL,
    WHITE,
)
from config import BAR_WIDTH_DAYS, CHART_FIGSIZE_WIDE

# ── Matplotlib global defaults ───────────────────────────────────────

plt.rcParams.update(
    {
        "font.family": ["Tahoma", "DejaVu Sans", "sans-serif"],
        "axes.facecolor": WHITE,
        "figure.facecolor": WHITE,
        "axes.edgecolor": GRAY_200,
        "axes.labelcolor": NAVY,
        "xtick.color": GRAY_600,
        "ytick.color": GRAY_600,
        "text.color": NAVY,
        "grid.color": GRAY_200,
        "grid.alpha": 0.5,
        "grid.linewidth": 0.5,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.framealpha": 0.95,
        "legend.edgecolor": GRAY_200,
        "legend.fontsize": 9,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
    }
)


# ── Shared helpers ───────────────────────────────────────────────────


def get_region_backlog(backlog_df: pd.DataFrame, region_label: str) -> float:
    """Return the hour-backlog for a single region, or 0 if not found."""
    match = backlog_df.loc[backlog_df["Region"] == region_label, "HOUR_BACKLOG"]
    return float(match.iloc[0]) if not match.empty else 0.0


def _monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
    """Aggregate scenario results to monthly level and compute cumulative backlog."""
    if df.empty:
        return pd.DataFrame()

    backlog = float(backlog)

    monthly = (
        df.groupby("DATE", as_index=False)[
            [
                "BASE_SUPPLY",
                "SCENARIO_SUPPLY",
                "DEMAND",
                "BASE_GAP",
                "SCENARIO_GAP",
                "SUPPLY_DELTA",
            ]
        ]
        .sum()
        .sort_values("DATE")
    )
    monthly["DATE"] = pd.to_datetime(monthly["DATE"])

    # Walk month-by-month so backlog floors at 0 each step rather than
    # allowing a simple cumsum to go negative and then clipping.
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


def _padded_limits(
    series: pd.Series,
    padding_frac: float = 0.2,
    min_pad: float = 1,
) -> tuple[float, float]:
    """Return (ymin, ymax) with symmetric padding around zero-inclusive bounds."""
    lo = min(series.min(), 0)
    hi = max(series.max(), 0)
    pad = max((hi - lo) * padding_frac, min_pad)
    return lo - pad, hi + pad


def _split_base_adjusted(
    monthly: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split monthly frame into base (no adjustment) and adjusted rows."""
    monthly["IS_ADJUSTED"] = monthly["SUPPLY_DELTA"] != 0
    monthly["DISPLAY_GAP"] = monthly["SCENARIO_GAP"].where(
        monthly["IS_ADJUSTED"],
        monthly["BASE_GAP"],
    )
    return monthly[~monthly["IS_ADJUSTED"]], monthly[monthly["IS_ADJUSTED"]]


def _thousands_formatter(x: float, _pos: int) -> str:
    """Format axis values as compact thousands (e.g. 1.2k, 15k)."""
    if abs(x) >= 1000:
        return f"{x / 1000:,.1f}k"
    return f"{x:,.0f}"


def _finalize(fig: Figure) -> Figure:
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


# ── Baseline & scenario line charts ─────────────────────────────────


def _line_chart(
    df: pd.DataFrame,
    supply_col: str,
    gap_col: str,
    title_prefix: str,
    region_label: str,
) -> Figure | None:
    """Shared implementation for baseline / scenario supply-vs-demand charts."""
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)

    # Supply line
    ax.plot(
        monthly["DATE"],
        monthly[supply_col],
        marker="o",
        markersize=6,
        color=LIGHT_BLUE,
        linewidth=2.5,
        label=f"{title_prefix} Supply",
        zorder=3,
    )
    # Demand line
    ax.plot(
        monthly["DATE"],
        monthly["DEMAND"],
        marker="D",
        markersize=5,
        color=ORANGE,
        linewidth=2.5,
        label="Demand",
        zorder=3,
    )
    # Gap line
    ax.plot(
        monthly["DATE"],
        monthly[gap_col],
        marker="s",
        markersize=5,
        color=NAVY,
        linewidth=2,
        linestyle="--",
        alpha=0.8,
        label=f"{title_prefix} Gap",
        zorder=3,
    )

    # Fill between supply and demand
    ax.fill_between(
        monthly["DATE"],
        monthly[supply_col],
        monthly["DEMAND"],
        alpha=0.08,
        color=LIGHT_BLUE,
    )

    # Zero line
    ax.axhline(0, linewidth=0.8, color=GRAY_600, linestyle="-", alpha=0.3)

    ax.set_title(f"{title_prefix} Supply vs Demand — {region_label}")
    ax.set_xlabel("")
    ax.set_ylabel("Hours")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_thousands_formatter))
    ax.legend(loc="upper left", framealpha=0.95)

    return _finalize(fig)


def baseline_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
) -> Figure | None:
    return _line_chart(df, "BASE_SUPPLY", "BASE_GAP", "Baseline", region_label)


def scenario_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
) -> Figure | None:
    return _line_chart(df, "SCENARIO_SUPPLY", "SCENARIO_GAP", "Scenario", region_label)


# ── Gap bar chart ────────────────────────────────────────────────────


def gap_bar_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
) -> Figure | None:
    """Baseline vs scenario gap as side-by-side bars with data labels."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)

    bar_kwargs = dict(width=BAR_WIDTH_DAYS, edgecolor="white", linewidth=0.5, zorder=2)

    bars_base = ax.bar(
        base_months["DATE"],
        base_months["DISPLAY_GAP"],
        color=LIGHT_BLUE,
        label="Baseline Gap",
        alpha=0.85,
        **bar_kwargs,
    )
    bars_scenario = ax.bar(
        adjusted_months["DATE"],
        adjusted_months["DISPLAY_GAP"],
        color=TEAL,
        label="Scenario Gap",
        alpha=0.85,
        **bar_kwargs,
    )
    ax.axhline(0, linewidth=0.8, color=NAVY, alpha=0.4)

    # Data labels on every bar
    for bars, color in [(bars_base, NAVY), (bars_scenario, NAVY)]:
        for bar in bars:
            val = bar.get_height()
            va = "bottom" if val >= 0 else "top"
            offset = 4 if val >= 0 else -4
            ax.annotate(
                f"{val:,.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, offset),
                textcoords="offset points",
                ha="center",
                va=va,
                fontsize=7.5,
                fontweight="bold",
                color=color,
            )

    ax.set_title(f"Supply vs Demand Gap — {region_label}")
    ax.set_xlabel("")
    ax.set_ylabel("Gap (hrs)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_thousands_formatter))
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=2,
        framealpha=0.95,
    )

    return _finalize(fig)


# ── Backlog trend chart ──────────────────────────────────────────────


def backlog_trend_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
) -> Figure | None:
    """Cumulative backlog (hours) on left axis, normalised backlog on right axis."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    monthly["NORMALIZED_BACKLOG"] = (
        monthly["SCENARIO_GAP_CUMSUM"]
        / monthly["SCENARIO_SUPPLY"].replace(0, float("nan"))
    )

    fig, ax_hours = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax_norm = ax_hours.twinx()

    # Cumulative backlog line (left axis)
    ax_hours.plot(
        monthly["DATE"],
        monthly["SCENARIO_GAP_CUMSUM"],
        marker="o",
        markersize=7,
        label="Cumulative Backlog (hrs)",
        color=ORANGE,
        linewidth=2.5,
        markerfacecolor="white",
        markeredgecolor=ORANGE,
        markeredgewidth=2,
        zorder=4,
    )
    ax_hours.fill_between(
        monthly["DATE"],
        monthly["SCENARIO_GAP_CUMSUM"],
        alpha=0.08,
        color=ORANGE,
    )

    # Normalised backlog line (right axis)
    ax_norm.plot(
        monthly["DATE"],
        monthly["NORMALIZED_BACKLOG"],
        marker="s",
        markersize=6,
        linestyle="--",
        label="Normalized Backlog (Squad-Months)",
        color=GOLD,
        linewidth=2,
        markerfacecolor="white",
        markeredgecolor=GOLD,
        markeredgewidth=2,
        zorder=4,
    )

    # Data labels on every point
    for i in range(len(monthly)):
        x = monthly["DATE"].iloc[i]

        y_hrs = monthly["SCENARIO_GAP_CUMSUM"].iloc[i]
        ax_hours.annotate(
            f"{y_hrs:,.0f}",
            xy=(x, y_hrs),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            fontweight="bold",
            color=NAVY,
        )

        y_norm = monthly["NORMALIZED_BACKLOG"].iloc[i]
        ax_norm.annotate(
            f"{y_norm:.1f}",
            xy=(x, y_norm),
            xytext=(0, -12),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=7.5,
            fontweight="bold",
            color=NAVY,
        )

    # Axis formatting
    ax_hours.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], padding_frac=0.15))
    ax_norm.set_ylim(
        *_padded_limits(monthly["NORMALIZED_BACKLOG"], padding_frac=0.15, min_pad=0.1)
    )

    ax_hours.set_title(f"Backlog Trend — {region_label}")
    ax_hours.set_xlabel("")
    ax_hours.set_ylabel("Cumulative Backlog (hrs)", color=ORANGE)
    ax_hours.yaxis.set_major_formatter(mticker.FuncFormatter(_thousands_formatter))
    ax_hours.tick_params(axis="y", labelcolor=ORANGE)

    ax_norm.set_ylabel("Normalized Backlog (Squad-Months)", color=GOLD)
    ax_norm.tick_params(axis="y", labelcolor=GOLD)
    ax_norm.spines["right"].set_edgecolor(GOLD)

    # Combined legend
    h1, l1 = ax_hours.get_legend_handles_labels()
    h2, l2 = ax_norm.get_legend_handles_labels()
    ax_hours.legend(
        h1 + h2,
        l1 + l2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=2,
        framealpha=0.95,
    )

    return _finalize(fig)


# ── Legacy wrapper (kept for backward compatibility) ─────────────────


def supply_delta_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
) -> Figure | None:
    """Deprecated — use gap_bar_chart and backlog_trend_chart instead."""
    return gap_bar_chart(df, region_label=region_label, backlog=backlog)
