"""Matplotlib chart builders for the Supply & Demand app."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from config import BAR_WIDTH_DAYS, CHART_FIGSIZE, CHART_FIGSIZE_SMALL


# ── Shared helpers ───────────────────────────────────────────────────────────

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
    supply_col: str,
    gap_col: str,
    title_prefix: str,
    region_label: str,
) -> plt.Figure | None:
    """Shared implementation for baseline / scenario supply-vs-demand charts."""
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_SMALL)
    ax.plot(monthly["DATE"], monthly[supply_col], marker="o", label=f"{title_prefix} Supply")
    ax.plot(monthly["DATE"], monthly["DEMAND"], marker="o", label="Demand")
    ax.plot(monthly["DATE"], monthly[gap_col], marker="o", label=f"{title_prefix} Gap")

    ax.set_title(f"{title_prefix} Supply vs Demand vs Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    return fig


def baseline_supply_demand_with_gap(
    df: pd.DataFrame, region_label: str = "All regions",
) -> plt.Figure | None:
    return _line_chart(df, "BASE_SUPPLY", "BASE_GAP", "Baseline", region_label)


def scenario_supply_demand_with_gap(
    df: pd.DataFrame, region_label: str = "All regions",
) -> plt.Figure | None:
    return _line_chart(df, "SCENARIO_SUPPLY", "SCENARIO_GAP", "Scenario", region_label)


# ── Backlog summary chart ────────────────────────────────────────────────────

def supply_delta_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
) -> plt.Figure | None:
    """Gap bars + cumulative backlog line + normalised backlog line."""
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    base_months, adjusted_months = _split_base_adjusted(monthly)

    monthly["NORMALIZED_BACKLOG"] = (
        monthly["SCENARIO_GAP_CUMSUM"] / monthly["SCENARIO_SUPPLY"]
    )

    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE)
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    # Gap bars
    ax1.bar(base_months["DATE"], base_months["DISPLAY_GAP"],
            width=BAR_WIDTH_DAYS, label="Baseline Gap")
    ax1.bar(adjusted_months["DATE"], adjusted_months["DISPLAY_GAP"],
            width=BAR_WIDTH_DAYS, label="Scenario Gap")
    ax1.axhline(0, linewidth=1)

    # Cumulative backlog line
    ax2.plot(monthly["DATE"], monthly["SCENARIO_GAP_CUMSUM"],
             marker="o", label="Cumulative Backlog (hours)",
             color="red", markerfacecolor="white", markeredgecolor="black")

    # Normalised backlog line
    ax3.plot(monthly["DATE"], monthly["NORMALIZED_BACKLOG"],
             marker="s", linestyle="--", label="Normalized Backlog (Squad-Months)",
             color="green", markerfacecolor="white", markeredgecolor="black")

    # Sparse annotations (first, middle, last)
    label_idx = sorted({0, len(monthly) // 2, len(monthly) - 1})
    label_idx = [i for i in label_idx if 0 <= i < len(monthly)]

    for i in label_idx:
        x = monthly["DATE"].iloc[i]
        y_bl = monthly["SCENARIO_GAP_CUMSUM"].iloc[i]
        ax2.annotate(f"{y_bl:,.0f}", xy=(x, y_bl), xytext=(0, 10),
                     textcoords="offset points", ha="center", va="bottom")

        y_norm = monthly["NORMALIZED_BACKLOG"].iloc[i]
        ax3.annotate(f"{y_norm:.1f}", xy=(x, y_norm), xytext=(0, -14),
                     textcoords="offset points", ha="center", va="top")

    # Axis limits
    ax1.set_ylim(*_padded_limits(monthly["DISPLAY_GAP"]))
    ax2.set_ylim(*_padded_limits(monthly["SCENARIO_GAP_CUMSUM"], padding_frac=0.1))
    ax3.set_ylim(*_padded_limits(monthly["NORMALIZED_BACKLOG"], padding_frac=0.1, min_pad=0.1))

    # Labels & legend
    ax1.set_title(f"Backlog Summary - {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Supply Vs Demand Gap (hours)")
    ax2.set_ylabel("")
    ax3.set_ylabel("")
    ax2.set_yticks([])
    ax3.set_yticks([])

    handles = sum((a.get_legend_handles_labels()[0] for a in (ax1, ax2, ax3)), [])
    labels = sum((a.get_legend_handles_labels()[1] for a in (ax1, ax2, ax3)), [])
    ax1.legend(handles, labels, loc=7, bbox_to_anchor=(1.3, 0.5), ncol=1)

    ax1.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig
