"""Scenario engine — pure-function pipeline that computes supply-vs-demand gaps.

Public API
----------
run_scenario(...)  →  pd.DataFrame with columns:
    CCRID, PROJECT_NAME, REGION, DATE,
    BASE_SUPPLY, SCENARIO_SUPPLY, SUPPLY_DELTA,
    DEMAND, BASE_GAP, SCENARIO_GAP, NET_BACKLOG
"""

from __future__ import annotations

import pandas as pd

from config import HOURS_PER_DAY
from data.snowflake import get_demand, get_demand_weight, get_supply, get_working_days

_OUTPUT_COLUMNS = [
    "CCRID", "PROJECT_NAME", "REGION", "DATE",
    "BASE_SUPPLY", "SCENARIO_SUPPLY", "SUPPLY_DELTA",
    "DEMAND", "BASE_GAP", "SCENARIO_GAP", "NET_BACKLOG",
]

_NUMERIC_COLUMNS = [
    "BASE_SUPPLY", "SCENARIO_SUPPLY", "SUPPLY_DELTA",
    "DEMAND", "BASE_GAP", "SCENARIO_GAP", "NET_BACKLOG",
]


def run_scenario(
    regions: list[str],
    adjustments: dict[str, int],
    start_date,
    end_date,
    adjustment_start_date,
    pct_decrease: float,
    vac_days_per_month: float,
    sick_days_per_month: float,
) -> pd.DataFrame:
    """Run a single scenario and return the final output DataFrame."""
    supply = _filter_supply(regions)
    wd = _prepare_working_days(start_date, end_date)
    adj_df = _adjustments_to_df(regions, adjustments)

    expanded = _expand_supply(
        wd, supply, adj_df,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        absence_days=float(vac_days_per_month) + float(sick_days_per_month),
    )

    allocated = _allocate_to_projects(expanded, _prepare_weights())
    demand = _prepare_demand()
    return _assemble_output(allocated, demand)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _filter_supply(regions: list[str]) -> pd.DataFrame:
    return get_supply().loc[lambda d: d["REGION"].isin(regions)].copy()


def _prepare_working_days(start_date, end_date) -> pd.DataFrame:
    wd = get_working_days(start_date, end_date).copy()
    wd["MONTH_START"] = pd.to_datetime(wd["MONTH_START"])
    wd["MONTH_NUMBER"] = wd["MONTH_START"].dt.month
    return wd[["MONTH_START", "MONTH_NUMBER", "BUSINESS_DAYS"]]


def _adjustments_to_df(regions: list[str], adjustments: dict[str, int]) -> pd.DataFrame:
    return pd.DataFrame({
        "REGION": regions,
        "ADJUSTMENT": [int(adjustments.get(r, 0)) for r in regions],
    })


def _expand_supply(
    wd: pd.DataFrame,
    supply: pd.DataFrame,
    adj_df: pd.DataFrame,
    *,
    adjustment_start_date,
    pct_decrease: float,
    absence_days: float,
) -> pd.DataFrame:
    """Cross-join months × regions, apply headcount adjustments, compute hours."""
    expanded = (
        wd.merge(supply, on="MONTH_NUMBER", how="left")
          .merge(adj_df, on="REGION", how="left")
    )
    expanded["ADJUSTMENT"] = expanded["ADJUSTMENT"].fillna(0)

    prod_mult = 1 - float(pct_decrease)
    adj_start_ts = pd.to_datetime(adjustment_start_date)

    # Headcount
    expanded["BASE_HEADCOUNT"] = expanded["COUNT"]
    expanded["SCENARIO_HEADCOUNT"] = expanded["COUNT"]
    mask = expanded["MONTH_START"] >= adj_start_ts
    expanded.loc[mask, "SCENARIO_HEADCOUNT"] = expanded["COUNT"] + expanded["ADJUSTMENT"]

    # Net business days
    expanded["NET_BUSINESS_DAYS"] = (expanded["BUSINESS_DAYS"] - absence_days).clip(lower=0)

    # Supply hours
    expanded["BASE_GROSS_SUPPLY_HOURS"] = (
        expanded["BASE_HEADCOUNT"] * expanded["NET_BUSINESS_DAYS"] * HOURS_PER_DAY
    )
    expanded["SCENARIO_GROSS_SUPPLY_HOURS"] = (
        expanded["SCENARIO_HEADCOUNT"] * expanded["NET_BUSINESS_DAYS"] * HOURS_PER_DAY
    )
    expanded["BASE_NET_SUPPLY_HOURS"] = expanded["BASE_GROSS_SUPPLY_HOURS"] * prod_mult
    expanded["SCENARIO_NET_SUPPLY_HOURS"] = expanded["SCENARIO_GROSS_SUPPLY_HOURS"] * prod_mult

    return expanded


def _prepare_weights() -> pd.DataFrame:
    weights = get_demand_weight().rename(columns={"SERVICE_REGION_ST": "REGION"})
    return weights[["CCRID", "REGION", "MONTH_NUMBER", "ALLOCATION"]]


def _allocate_to_projects(expanded: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    alloc = expanded.merge(weights, on=["MONTH_NUMBER", "REGION"], how="inner")
    alloc["BASE_PROJECT_SUPPLY_HOURS"] = alloc["BASE_NET_SUPPLY_HOURS"] * alloc["ALLOCATION"]
    alloc["SCENARIO_PROJECT_SUPPLY_HOURS"] = alloc["SCENARIO_NET_SUPPLY_HOURS"] * alloc["ALLOCATION"]
    return alloc


def _prepare_demand() -> pd.DataFrame:
    demand = get_demand().rename(columns={"HOURS": "DEMAND_HOURS"})
    return demand[["CCRID", "PROJECT_NAME", "MONTH_NUMBER", "DEMAND_HOURS"]]


def _assemble_output(alloc: pd.DataFrame, demand: pd.DataFrame) -> pd.DataFrame:
    final = alloc.merge(demand, on=["CCRID", "MONTH_NUMBER"], how="left")
    final["DEMAND_HOURS"] = final["DEMAND_HOURS"].fillna(0)

    final["BASE_GAP_HOURS"] = final["BASE_PROJECT_SUPPLY_HOURS"] - final["DEMAND_HOURS"]
    final["SCENARIO_GAP_HOURS"] = final["SCENARIO_PROJECT_SUPPLY_HOURS"] - final["DEMAND_HOURS"]
    final["SUPPLY_DELTA_HOURS"] = (
        final["SCENARIO_PROJECT_SUPPLY_HOURS"] - final["BASE_PROJECT_SUPPLY_HOURS"]
    )
    final["NET_BACKLOG"] = (
        final["SCENARIO_GAP_HOURS"] - final["BASE_GAP_HOURS"] - final["DEMAND_HOURS"]
    )

    final = final.rename(columns={
        "MONTH_START": "DATE",
        "BASE_PROJECT_SUPPLY_HOURS": "BASE_SUPPLY",
        "SCENARIO_PROJECT_SUPPLY_HOURS": "SCENARIO_SUPPLY",
        "SUPPLY_DELTA_HOURS": "SUPPLY_DELTA",
        "DEMAND_HOURS": "DEMAND",
        "BASE_GAP_HOURS": "BASE_GAP",
        "SCENARIO_GAP_HOURS": "SCENARIO_GAP",
    })

    final[_NUMERIC_COLUMNS] = final[_NUMERIC_COLUMNS].round(1)
    return (
        final[_OUTPUT_COLUMNS]
        .sort_values(["DATE", "REGION", "CCRID"])
        .reset_index(drop=True)
    )
