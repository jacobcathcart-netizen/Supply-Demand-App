import matplotlib.pyplot as plt
import pandas as pd


def get_region_backlog(backlog_df: pd.DataFrame, region_label: str) -> float:
    match = backlog_df.loc[backlog_df["Region"] == region_label, "HOUR_BACKLOG"]
    return float(match.iloc[0]) if not match.empty else 0.0


def _monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

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
            BASE_GAP_CUMSUM=lambda d: -d["BASE_GAP"].cumsum(),
            SCENARIO_GAP_CUMSUM=lambda d: backlog - d["SCENARIO_GAP"].cumsum(),
        )
    )

    monthly["DATE"] = pd.to_datetime(monthly["DATE"])
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

    fig, ax = plt.subplots(figsize=(12, 4))

    base_months = monthly[~monthly["IS_ADJUSTED"]]
    adjusted_months = monthly[monthly["IS_ADJUSTED"]]

    ax.bar(
        base_months["DATE"],
        base_months["DISPLAY_GAP"],
        width=15,
        label="Baseline Gap",
    )
    ax.bar(
        adjusted_months["DATE"],
        adjusted_months["DISPLAY_GAP"],
        width=15,
        label="Scenario Gap",
    )
    ax.plot(
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
        ax.annotate(
            f"{y:,.0f}",
            xy=(x, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=valign,
        )

    ax.axhline(0, linewidth=1)

    y_min = min(
        monthly["DISPLAY_GAP"].min(),
        monthly["SCENARIO_GAP_CUMSUM"].min(),
        0,
    )
    y_max = max(
        monthly["DISPLAY_GAP"].max(),
        monthly["SCENARIO_GAP_CUMSUM"].max(),
        0,
    )
    padding = max((y_max - y_min) * 0.2, 1)

    ax.set_ylim(y_min - padding, y_max + padding)
    ax.set_title(f"Monthly Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()

    return fig