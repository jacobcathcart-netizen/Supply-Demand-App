import matplotlib.pyplot as plt
import pandas as pd


def _monthly_totals(df: pd.DataFrame) -> pd.DataFrame:
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
    )
    monthly["DATE"] = pd.to_datetime(monthly["DATE"])
    return monthly


def baseline_supply_demand_with_gap(df: pd.DataFrame, region_label: str = "All regions"):
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly["DATE"], monthly["BASE_SUPPLY"], marker="o", label="Baseline Supply")
    ax.plot(monthly["DATE"], monthly["DEMAND"], marker="o", label="Demand")
    ax.plot(monthly["DATE"], monthly["BASE_GAP"], marker="o", label="Baseline Gap")

    ax.set_title(f"Baseline Supply vs Demand vs Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return fig


def scenario_supply_demand_with_gap(df: pd.DataFrame, region_label: str = "All regions"):
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(monthly["DATE"], monthly["SCENARIO_SUPPLY"], marker="o", label="Scenario Supply")
    ax.plot(monthly["DATE"], monthly["DEMAND"], marker="o", label="Demand")
    ax.plot(monthly["DATE"], monthly["SCENARIO_GAP"], marker="o", label="Scenario Gap")

    ax.set_title(f"Scenario Supply vs Demand vs Gap - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    return fig


def supply_delta_chart(df: pd.DataFrame, region_label: str = "All regions"):
    monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(monthly["DATE"], monthly["SUPPLY_DELTA"], width=20)
    ax.axhline(0, linewidth=1)
    ax.set_ylim(
        min(monthly["SUPPLY_DELTA"].min(), 0) * 1.1,
        max(monthly["SUPPLY_DELTA"].max(), 0) * 1.1 if monthly["SUPPLY_DELTA"].max() != 0 else 1,
    )
    ax.set_title(f"Supply Delta - {region_label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Hours")
    ax.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()

    return fig