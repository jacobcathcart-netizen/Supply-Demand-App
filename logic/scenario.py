"""Scenario engine: builds a supply-vs-demand comparison DataFrame.

The public entry-point is :func:`run_scenario`.  Every private helper is
a pure-ish function that receives and returns DataFrames so the pipeline
is easy to test in isolation.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from config import HOURS_PER_DAY
from data.snowflake import get_demand, get_demand_weight, get_supply, get_working_days

# ── Column sets (used for selection / ordering) ─────────────────────

_FINAL_COLUMNS: list[str] = [
    "CCRID",
    "PROJECT_NAME",
    "REGION",
    "DATE",
    "BASE_SUPPLY",
    "SCENARIO_SUPPLY",
    "SUPPLY_DELTA",
    "DEMAND",
    "BASE_GAP",
    "SCENARIO_GAP",
]

_NUMERIC_COLUMNS: list[str] = [
    "BASE_SUPPLY",
    "SCENARIO_SUPPLY",
    "SUPPLY_DELTA",
    "DEMAND",
    "BASE_GAP",
    "SCENARIO_GAP",
]


# ── Public API ──────────────────────────────────────────────────────


def run_scenario(
    regions: list[str],
    adjustments: dict[str, int],
    start_date: date,
    end_date: date,
    adjustment_start_date: date,
    pct_decrease: float,
    vac_days_per_month: float,
    sick_days_per_month: float,
    excluded_ccrids: list[str] | None = None,
    custom_projects: list[dict] | None = None,
) -> pd.DataFrame:
    """Run a full scenario and return the result DataFrame.

    Parameters
    ----------
    regions:
        Regions to include.
    adjustments:
        Region → headcount delta mapping.
    start_date / end_date:
        Scenario date window.
    adjustment_start_date:
        Month from which headcount adjustments take effect.
    pct_decrease:
        Fraction of time lost to non-project work (0-1).
    vac_days_per_month / sick_days_per_month:
        Average absence days per FTE per month.
    excluded_ccrids:
        CCRIDs to exclude from demand and supply allocation.
    custom_projects:
        List of dicts with keys CCRID, PROJECT_NAME, REGION, TOTAL_HOURS.
        These are demand-only projects (supply = 0).

    Returns
    -------
    pd.DataFrame
        One row per (project, region, month) with supply, demand, and
        gap columns.
    """
    supply = _filter_supply(regions)
    working_days = _prepare_working_days(start_date, end_date)
    adj_df = _adjustments_to_df(regions, adjustments)

    expanded = _expand_supply(
        working_days=working_days,
        supply=supply,
        adj_df=adj_df,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        absence_days=float(vac_days_per_month) + float(sick_days_per_month),
    )

    weights = _prepare_weights()
    demand = _prepare_demand()

    # Filter out excluded projects
    if excluded_ccrids:
        weights = weights[~weights["CCRID"].isin(excluded_ccrids)]
        demand = demand[~demand["CCRID"].isin(excluded_ccrids)]

    # Add custom projects to demand and weights
    if custom_projects:
        custom_demand, custom_weights = _build_custom_demand_and_weights(
            custom_projects, working_days
        )
        demand = pd.concat([demand, custom_demand], ignore_index=True)
        weights = pd.concat([weights, custom_weights], ignore_index=True)

    # Recalculate allocation weights from demand proportions
    if excluded_ccrids or custom_projects:
        weights = _recalculate_weights_from_demand(weights, demand)

    allocated = _allocate_to_projects(expanded, weights)
    output = _assemble_output(allocated, demand)

    return output


# ── Pipeline steps ──────────────────────────────────────────────────


def _filter_supply(regions: list[str]) -> pd.DataFrame:
    return get_supply().loc[lambda d: d["REGION"].isin(regions)].copy()


def _prepare_working_days(start_date: date, end_date: date) -> pd.DataFrame:
    wd = get_working_days(start_date, end_date).copy()
    wd["MONTH_START"] = pd.to_datetime(wd["MONTH_START"])
    wd["MONTH_NUMBER"] = wd["MONTH_START"].dt.month
    return wd[["MONTH_START", "MONTH_NUMBER", "BUSINESS_DAYS"]]


def _adjustments_to_df(
    regions: list[str], adjustments: dict[str, int]
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "REGION": regions,
            "ADJUSTMENT": [int(adjustments.get(r, 0)) for r in regions],
        }
    )


def _expand_supply(
    *,
    working_days: pd.DataFrame,
    supply: pd.DataFrame,
    adj_df: pd.DataFrame,
    adjustment_start_date: date,
    pct_decrease: float,
    absence_days: float,
) -> pd.DataFrame:
    """Cross-join months × regions, then compute supply hours."""
    df = (
        working_days.merge(supply, on="MONTH_NUMBER", how="left")
        .merge(adj_df, on="REGION", how="left")
    )
    df["ADJUSTMENT"] = df["ADJUSTMENT"].fillna(0)

    productivity = 1 - float(pct_decrease)
    adj_start = pd.to_datetime(adjustment_start_date)

    # Headcount
    df["BASE_HEADCOUNT"] = df["COUNT"]
    df["SCENARIO_HEADCOUNT"] = df["COUNT"]
    mask = df["MONTH_START"] >= adj_start
    df.loc[mask, "SCENARIO_HEADCOUNT"] = df["COUNT"] + df["ADJUSTMENT"]

    # Available days after absences
    df["NET_BUSINESS_DAYS"] = (df["BUSINESS_DAYS"] - absence_days).clip(lower=0)

    # Hours = headcount × net days × hours/day × productivity
    df["BASE_GROSS_SUPPLY_HOURS"] = (
        df["BASE_HEADCOUNT"] * df["NET_BUSINESS_DAYS"] * HOURS_PER_DAY
    )
    df["SCENARIO_GROSS_SUPPLY_HOURS"] = (
        df["SCENARIO_HEADCOUNT"] * df["NET_BUSINESS_DAYS"] * HOURS_PER_DAY
    )
    df["BASE_NET_SUPPLY_HOURS"] = df["BASE_GROSS_SUPPLY_HOURS"] * productivity
    df["SCENARIO_NET_SUPPLY_HOURS"] = df["SCENARIO_GROSS_SUPPLY_HOURS"] * productivity

    return df


def _prepare_weights() -> pd.DataFrame:
    weights = get_demand_weight().copy()
    weights = weights.rename(columns={"SERVICE_REGION_ST": "REGION"})
    return weights[["CCRID", "REGION", "MONTH_NUMBER", "ALLOCATION"]]


def _recalculate_weights_from_demand(
    weights: pd.DataFrame,
    demand: pd.DataFrame,
) -> pd.DataFrame:
    """Recalculate ALLOCATION as each project's share of regional demand."""
    merged = weights[["CCRID", "REGION", "MONTH_NUMBER"]].merge(
        demand[["CCRID", "MONTH_NUMBER", "DEMAND_HOURS"]],
        on=["CCRID", "MONTH_NUMBER"],
        how="left",
    )
    merged["DEMAND_HOURS"] = merged["DEMAND_HOURS"].fillna(0)

    group_total = merged.groupby(["REGION", "MONTH_NUMBER"])[
        "DEMAND_HOURS"
    ].transform("sum")
    merged["ALLOCATION"] = merged["DEMAND_HOURS"] / group_total.replace(0, 1)

    return merged[["CCRID", "REGION", "MONTH_NUMBER", "ALLOCATION"]]


def _allocate_to_projects(
    expanded: pd.DataFrame, weights: pd.DataFrame
) -> pd.DataFrame:
    """Distribute regional supply hours across projects using weights."""
    merged = expanded.merge(weights, on=["MONTH_NUMBER", "REGION"], how="inner")
    merged["BASE_PROJECT_SUPPLY_HOURS"] = (
        merged["BASE_NET_SUPPLY_HOURS"] * merged["ALLOCATION"]
    )
    merged["SCENARIO_PROJECT_SUPPLY_HOURS"] = (
        merged["SCENARIO_NET_SUPPLY_HOURS"] * merged["ALLOCATION"]
    )
    return merged

def _prepare_demand() -> pd.DataFrame:
    demand = get_demand().rename(columns={"HOURS": "DEMAND_HOURS"})
    return demand[["CCRID", "PROJECT_NAME", "MONTH_NUMBER", "DEMAND_HOURS"]]


def _assemble_output(
    allocated: pd.DataFrame, demand: pd.DataFrame
) -> pd.DataFrame:
    """Join allocated supply with demand and compute gaps."""
    df = allocated.merge(demand, on=["CCRID", "MONTH_NUMBER"], how="left")
    df["DEMAND_HOURS"] = df["DEMAND_HOURS"].fillna(0)

    df["BASE_GAP_HOURS"] = df["BASE_PROJECT_SUPPLY_HOURS"] - df["DEMAND_HOURS"]
    df["SCENARIO_GAP_HOURS"] = (
        df["SCENARIO_PROJECT_SUPPLY_HOURS"] - df["DEMAND_HOURS"]
    )
    df["SUPPLY_DELTA_HOURS"] = (
        df["SCENARIO_PROJECT_SUPPLY_HOURS"] - df["BASE_PROJECT_SUPPLY_HOURS"]
    )
    df = df.rename(
        columns={
            "MONTH_START": "DATE",
            "BASE_PROJECT_SUPPLY_HOURS": "BASE_SUPPLY",
            "SCENARIO_PROJECT_SUPPLY_HOURS": "SCENARIO_SUPPLY",
            "SUPPLY_DELTA_HOURS": "SUPPLY_DELTA",
            "DEMAND_HOURS": "DEMAND",
            "BASE_GAP_HOURS": "BASE_GAP",
            "SCENARIO_GAP_HOURS": "SCENARIO_GAP",
        }
    )

    df[_NUMERIC_COLUMNS] = df[_NUMERIC_COLUMNS].round(1)
    df = df[_FINAL_COLUMNS].copy()
    return df.sort_values(["DATE", "REGION", "CCRID"]).reset_index(drop=True)


def _build_custom_demand_and_weights(
    custom_projects: list[dict],
    working_days: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create demand and weight entries for custom projects.

    Returns a (demand, weights) tuple so custom projects participate in
    the main allocation pipeline rather than being appended as zero-supply
    rows.
    """
    demand_rows: list[dict] = []
    weight_rows: list[dict] = []
    for proj in custom_projects:
        start = pd.to_datetime(proj.get("START_DATE"))
        eligible = working_days[working_days["MONTH_START"] >= start]
        n_months = max(len(eligible), 1)
        # TOTAL_HOURS is yearly demand — normalize to the scenario duration,
        # then distribute proportionally by working days per month.
        scenario_demand = proj["TOTAL_HOURS"] * (n_months / 12)
        total_working_days = max(eligible["BUSINESS_DAYS"].sum(), 1)
        for _, wd_row in eligible.iterrows():
            month_num = wd_row["MONTH_NUMBER"]
            monthly_demand = scenario_demand * (wd_row["BUSINESS_DAYS"] / total_working_days)
            demand_rows.append(
                {
                    "CCRID": proj["CCRID"],
                    "PROJECT_NAME": proj["PROJECT_NAME"],
                    "MONTH_NUMBER": month_num,
                    "DEMAND_HOURS": round(monthly_demand, 1),
                }
            )
            weight_rows.append(
                {
                    "CCRID": proj["CCRID"],
                    "REGION": proj["REGION"],
                    "MONTH_NUMBER": month_num,
                    "ALLOCATION": 0.0,  # placeholder; recalculated later
                }
            )
    demand_df = (
        pd.DataFrame(demand_rows)
        if demand_rows
        else pd.DataFrame(columns=["CCRID", "PROJECT_NAME", "MONTH_NUMBER", "DEMAND_HOURS"])
    )
    weights_df = (
        pd.DataFrame(weight_rows)
        if weight_rows
        else pd.DataFrame(columns=["CCRID", "REGION", "MONTH_NUMBER", "ALLOCATION"])
    )
    return demand_df, weights_df
