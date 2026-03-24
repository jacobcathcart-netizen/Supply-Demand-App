import matplotlib.pyplot as plt
import pandas as pd


def get_region_backlog(backlog_df: pd.DataFrame, region_label: str) -> float:
    match = backlog_df.loc[backlog_df["Region"] == region_label, "HOUR_BACKLOG"]
    return float(match.iloc[0]) if not match.empty else 0.0


def _monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
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
        .assign(
            BASE_GAP_CUMSUM=lambda d: -pd.to_numeric(d["BASE_GAP"], errors="coerce").cumsum(),
            SCENARIO_GAP_CUMSUM=lambda d: backlog
            + (-pd.to_numeric(d["SCENARIO_GAP"], errors="coerce")).cumsum(),
        )
    )

    monthly["DATE"] = pd.to_datetime(monthly["DATE"])
    monthly["BACKLOG_AS_SUPPLY"] = (
        monthly["SCENARIO_GAP_CUMSUM"] / monthly["SCENARIO_SUPPLY"]
    )

    return monthly


def baseline_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
):
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        monthly["DATE"],
        monthly["BASE_SUPPLY"],
        marker="o",
        label="Baseline Supply",
    )
    ax.plot(
        monthly["DATE"],
        monthly["DEMAND"],
        marker="o",
        label="Demand",
    )
    ax.plot(
        monthly["DATE"],
        monthly["BASE_GAP"],
        marker="o",
        label="Baseline Gap",
    )

    ax.set_title(f"Baseline Supply vs Demand vs Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return fig


def scenario_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
):
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        monthly["DATE"],
        monthly["SCENARIO_SUPPLY"],
        marker="o",
        label="Scenario Supply",
    )
    ax.plot(
        monthly["DATE"],
        monthly["DEMAND"],
        marker="o",
        label="Demand",
    )
    ax.plot(
        monthly["DATE"],
        monthly["SCENARIO_GAP"],
        marker="o",
        label="Scenario Gap",
    )

    ax.set_title(f"Scenario Supply vs Demand vs Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return fig


def supply_delta_chart2(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
):
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    monthly["IS_ADJUSTED"] = monthly["SUPPLY_DELTA"] != 0
    monthly["DISPLAY_GAP"] = monthly["SCENARIO_GAP"].where(
        monthly["IS_ADJUSTED"],
        monthly["BASE_GAP"],
    )

    base_months = monthly[~monthly["IS_ADJUSTED"]]
    adjusted_months = monthly[monthly["IS_ADJUSTED"]]

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(12, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    ax1.bar(
        base_months["DATE"],
        base_months["DISPLAY_GAP"],
        width=15,
        label="Baseline Gap",
    )
    ax1.bar(
        adjusted_months["DATE"],
        adjusted_months["DISPLAY_GAP"],
        width=15,
        label="Scenario Gap",
    )
    ax1.axhline(0, linewidth=1)

    gap_min = min(monthly["DISPLAY_GAP"].min(), 0)
    gap_max = max(monthly["DISPLAY_GAP"].max(), 0)
    gap_padding = max((gap_max - gap_min) * 0.2, 1)

    ax1.set_ylim(gap_min - gap_padding, gap_max + gap_padding)
    ax1.set_title(f"Monthly Gap and Backlog - {region_label}")
    ax1.set_ylabel("Monthly Gap Hours")
    ax1.legend()
    ax1.grid(True, axis="y", alpha=0.3)

    ax2.plot(
        monthly["DATE"],
        monthly["SCENARIO_GAP_CUMSUM"],
        marker="o",
        label="Cumulative Backlog",
        color="red",
        markerfacecolor="white",
        markeredgecolor="black",
    )

    for x, y in zip(monthly["DATE"], monthly["SCENARIO_GAP_CUMSUM"]):
        offset = 8 if y >= 0 else -12
        valign = "bottom" if y >= 0 else "top"
        ax2.annotate(
            f"{y:,.0f}",
            xy=(x, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=valign,
        )

    backlog_min = min(monthly["SCENARIO_GAP_CUMSUM"].min(), 0)
    backlog_max = max(monthly["SCENARIO_GAP_CUMSUM"].max(), 0)
    backlog_padding = max((backlog_max - backlog_min) * 0.1, 1)

    ax2.set_ylim(backlog_min - backlog_padding, backlog_max + backlog_padding)
    ax2.set_ylabel("Backlog Hours")
    ax2.set_xlabel("Month")
    ax2.legend()
    ax2.grid(True, axis="y", alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

def supply_delta_chart3(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
):
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    monthly["IS_ADJUSTED"] = monthly["SUPPLY_DELTA"] != 0
    monthly["DISPLAY_GAP"] = monthly["SCENARIO_GAP"].where(
        monthly["IS_ADJUSTED"],
        monthly["BASE_GAP"],
    )
    monthly["NORMALIZED_BACKLOG"] = (
        monthly["SCENARIO_GAP_CUMSUM"] / monthly["SCENARIO_SUPPLY"]
    )

    base_months = monthly[~monthly["IS_ADJUSTED"]]
    adjusted_months = monthly[monthly["IS_ADJUSTED"]]

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    #ax3.spines["right"].set_position(("outward", 60))

    ax1.bar(
        base_months["DATE"],
        base_months["DISPLAY_GAP"],
        width=15,
        label="Baseline Gap",
    )
    ax1.bar(
        adjusted_months["DATE"],
        adjusted_months["DISPLAY_GAP"],
        width=15,
        label="Scenario Gap",
    )
    ax1.axhline(0, linewidth=1)

    ax2.plot(
        monthly["DATE"],
        monthly["SCENARIO_GAP_CUMSUM"],
        marker="o",
        label="Cumulative Backlog",
        color="red",
        markerfacecolor="white",
        markeredgecolor="black",
    )

    ax3.plot(
        monthly["DATE"],
        monthly["NORMALIZED_BACKLOG"],
        marker="s",
        linestyle="--",
        label="Normalized Backlog",
        color="green",
        markerfacecolor="white",
        markeredgecolor="black",
    )

    for x, y in zip(monthly["DATE"], monthly["SCENARIO_GAP_CUMSUM"]):
        offset = 8 if y >= 0 else -12
        valign = "bottom" if y >= 0 else "top"
        ax2.annotate(
            f"{y:,.0f}",
            xy=(x, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=valign,
        )

    for x, y in zip(monthly["DATE"], monthly["NORMALIZED_BACKLOG"]):
        offset = 8 if y >= 0 else -12
        valign = "bottom" if y >= 0 else "top"
        ax3.annotate(
            f"{y:.2f}",
            xy=(x, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=valign,
        )

    gap_min = min(monthly["DISPLAY_GAP"].min(), 0)
    gap_max = max(monthly["DISPLAY_GAP"].max(), 0)
    gap_padding = max((gap_max - gap_min) * 0.2, 1)
    ax1.set_ylim(gap_min - gap_padding, gap_max + gap_padding)

    backlog_min = min(monthly["SCENARIO_GAP_CUMSUM"].min(), 0)
    backlog_max = max(monthly["SCENARIO_GAP_CUMSUM"].max(), 0)
    backlog_padding = max((backlog_max - backlog_min) * 0.1, 1)
    ax2.set_ylim(backlog_min - backlog_padding, backlog_max + backlog_padding)

    normalized_min = min(monthly["NORMALIZED_BACKLOG"].min(), 0)
    normalized_max = max(monthly["NORMALIZED_BACKLOG"].max(), 0)
    normalized_padding = max((normalized_max - normalized_min) * 0.1, 0.1)
    ax3.set_ylim(normalized_min - normalized_padding, normalized_max + normalized_padding)

    ax1.set_title(f"Monthly Gap - {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Gap Hours")
    ax2.set_ylabel("")
    ax3.set_ylabel("")
    ax2.set_yticks([])
    ax3.set_yticks([])
    

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(
        handles1 + handles2 + handles3,
        labels1 + labels2 + labels3,
        loc="upper right",
    )

    ax1.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig

def supply_delta_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
):
    monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    monthly["IS_ADJUSTED"] = monthly["SUPPLY_DELTA"] != 0
    monthly["DISPLAY_GAP"] = monthly["SCENARIO_GAP"].where(
        monthly["IS_ADJUSTED"],
        monthly["BASE_GAP"],
    )
    monthly["NORMALIZED_BACKLOG"] = (
        monthly["SCENARIO_GAP_CUMSUM"] / monthly["SCENARIO_SUPPLY"]
    )

    base_months = monthly[~monthly["IS_ADJUSTED"]]
    adjusted_months = monthly[monthly["IS_ADJUSTED"]]

    fig, ax1 = plt.subplots(figsize=(13, 5))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()

    #ax3.spines["right"].set_position(("outward", 60))

    ax1.bar(
        base_months["DATE"],
        base_months["DISPLAY_GAP"],
        width=15,
        label="Baseline Gap",
    )
    ax1.bar(
        adjusted_months["DATE"],
        adjusted_months["DISPLAY_GAP"],
        width=15,
        label="Scenario Gap",
    )
    ax1.axhline(0, linewidth=1)

    ax2.plot(
        monthly["DATE"],
        monthly["SCENARIO_GAP_CUMSUM"],
        marker="o",
        label="Cumulative Backlog",
        color="red",
        markerfacecolor="white",
        markeredgecolor="black",
    )

    ax3.plot(
        monthly["DATE"],
        monthly["NORMALIZED_BACKLOG"],
        marker="s",
        linestyle="--",
        label="Normalized Backlog",
        color="green",
        markerfacecolor="white",
        markeredgecolor="black",
    )

    label_idx = [0, len(monthly) // 2, len(monthly) - 1]
    label_idx = sorted(set(i for i in label_idx if 0 <= i < len(monthly)))

    for i in label_idx:
        x = monthly["DATE"].iloc[i]

        y_backlog = monthly["SCENARIO_GAP_CUMSUM"].iloc[i]
        ax2.annotate(
            f"{y_backlog:,.0f}",
            xy=(x, y_backlog),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )

        y_normalized = monthly["NORMALIZED_BACKLOG"].iloc[i]
        ax3.annotate(
            f"{y_normalized:.1f}",
            xy=(x, y_normalized),
            xytext=(0, -14),
            textcoords="offset points",
            ha="center",
            va="top",
        )

    gap_min = min(monthly["DISPLAY_GAP"].min(), 0)
    gap_max = max(monthly["DISPLAY_GAP"].max(), 0)
    gap_padding = max((gap_max - gap_min) * 0.2, 1)
    ax1.set_ylim(gap_min - gap_padding, gap_max + gap_padding)

    backlog_min = min(monthly["SCENARIO_GAP_CUMSUM"].min(), 0)
    backlog_max = max(monthly["SCENARIO_GAP_CUMSUM"].max(), 0)
    backlog_padding = max((backlog_max - backlog_min) * 0.1, 1)
    ax2.set_ylim(backlog_min - backlog_padding, backlog_max + backlog_padding)

    normalized_min = min(monthly["NORMALIZED_BACKLOG"].min(), 0)
    normalized_max = max(monthly["NORMALIZED_BACKLOG"].max(), 0)
    normalized_padding = max((normalized_max - normalized_min) * 0.1, 0.1)
    ax3.set_ylim(normalized_min - normalized_padding, normalized_max + normalized_padding)

    ax1.set_title(f"Monthly Gap - {region_label}")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Gap Hours")
    ax2.set_ylabel("")
    ax3.set_ylabel("")
    ax2.set_yticks([])
    ax3.set_yticks([])

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(
        handles1 + handles2 + handles3,
        labels1 + labels2 + labels3,
        loc=7,
        bbox_to_anchor=(1.2, .5),
        ncol=1,
    )

    ax1.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig