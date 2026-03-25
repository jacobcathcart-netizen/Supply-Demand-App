"""Unit tests for the scenario engine.

These tests exercise the pure-function helpers in ``logic.scenario``
without requiring a Snowflake connection — we patch the data-access
functions to return deterministic DataFrames.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

# We need to patch streamlit caching before importing the module under
# test, because the decorators run at import time.
import streamlit as st  # noqa: F401

from logic.scenario import (
    _adjustments_to_df,
    _assemble_output,
    _expand_supply,
    _filter_supply,
    _prepare_working_days,
    run_scenario,
)
from config import HOURS_PER_DAY


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture()
def supply_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "REGION": ["East", "East", "West", "West"],
            "MONTH_NUMBER": [1, 2, 1, 2],
            "COUNT": [10, 10, 5, 5],
        }
    )


@pytest.fixture()
def working_days_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "MONTH_START": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "BUSINESS_DAYS": [22, 20],
        }
    )


@pytest.fixture()
def weights_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SERVICE_REGION_ST": ["East", "East", "West", "West"],
            "CCRID": ["P001", "P001", "P002", "P002"],
            "MONTH_NUMBER": [1, 2, 1, 2],
            "ALLOCATION": [1.0, 1.0, 1.0, 1.0],
        }
    )


@pytest.fixture()
def demand_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CCRID": ["P001", "P001", "P002", "P002"],
            "PROJECT_NAME": ["Alpha", "Alpha", "Beta", "Beta"],
            "MONTH_NUMBER": [1, 2, 1, 2],
            "HOURS": [500, 500, 200, 200],
        }
    )


# ── Tests ───────────────────────────────────────────────────────────


class TestFilterSupply:
    def test_filters_to_selected_regions(self, supply_df: pd.DataFrame):
        with patch("logic.scenario.get_supply", return_value=supply_df):
            result = _filter_supply(["East"])
        assert list(result["REGION"].unique()) == ["East"]

    def test_empty_when_no_match(self, supply_df: pd.DataFrame):
        with patch("logic.scenario.get_supply", return_value=supply_df):
            result = _filter_supply(["North"])
        assert result.empty


class TestPrepareWorkingDays:
    def test_adds_month_number(self, working_days_df: pd.DataFrame):
        with patch("logic.scenario.get_working_days", return_value=working_days_df):
            result = _prepare_working_days(date(2025, 1, 1), date(2025, 2, 28))
        assert "MONTH_NUMBER" in result.columns
        assert list(result["MONTH_NUMBER"]) == [1, 2]


class TestAdjustmentsToDf:
    def test_creates_correct_dataframe(self):
        result = _adjustments_to_df(["East", "West"], {"East": 3, "West": -1})
        assert list(result["ADJUSTMENT"]) == [3, -1]

    def test_defaults_to_zero(self):
        result = _adjustments_to_df(["East"], {})
        assert list(result["ADJUSTMENT"]) == [0]


class TestExpandSupply:
    def test_scenario_headcount_includes_adjustment_after_start(self):
        wd = pd.DataFrame(
            {
                "MONTH_START": pd.to_datetime(["2025-01-01", "2025-02-01"]),
                "MONTH_NUMBER": [1, 2],
                "BUSINESS_DAYS": [22, 20],
            }
        )
        supply = pd.DataFrame(
            {"REGION": ["East", "East"], "MONTH_NUMBER": [1, 2], "COUNT": [10, 10]}
        )
        adj = pd.DataFrame({"REGION": ["East"], "ADJUSTMENT": [5]})

        result = _expand_supply(
            working_days=wd,
            supply=supply,
            adj_df=adj,
            adjustment_start_date=date(2025, 2, 1),
            pct_decrease=0.0,
            absence_days=0.0,
        )

        jan = result[result["MONTH_NUMBER"] == 1].iloc[0]
        feb = result[result["MONTH_NUMBER"] == 2].iloc[0]
        assert jan["SCENARIO_HEADCOUNT"] == 10  # before adjustment
        assert feb["SCENARIO_HEADCOUNT"] == 15  # after adjustment

    def test_absence_reduces_net_days(self):
        wd = pd.DataFrame(
            {
                "MONTH_START": pd.to_datetime(["2025-01-01"]),
                "MONTH_NUMBER": [1],
                "BUSINESS_DAYS": [22],
            }
        )
        supply = pd.DataFrame({"REGION": ["East"], "MONTH_NUMBER": [1], "COUNT": [1]})
        adj = pd.DataFrame({"REGION": ["East"], "ADJUSTMENT": [0]})

        result = _expand_supply(
            working_days=wd,
            supply=supply,
            adj_df=adj,
            adjustment_start_date=date(2025, 1, 1),
            pct_decrease=0.0,
            absence_days=2.0,
        )

        row = result.iloc[0]
        assert row["NET_BUSINESS_DAYS"] == 20
        assert row["BASE_GROSS_SUPPLY_HOURS"] == 20 * HOURS_PER_DAY


class TestAssembleOutput:
    def test_gap_is_supply_minus_demand(self):
        alloc = pd.DataFrame(
            {
                "CCRID": ["P001"],
                "MONTH_NUMBER": [1],
                "MONTH_START": pd.to_datetime(["2025-01-01"]),
                "REGION": ["East"],
                "BASE_PROJECT_SUPPLY_HOURS": [1000.0],
                "SCENARIO_PROJECT_SUPPLY_HOURS": [1200.0],
            }
        )
        demand = pd.DataFrame(
            {
                "CCRID": ["P001"],
                "PROJECT_NAME": ["Alpha"],
                "MONTH_NUMBER": [1],
                "DEMAND_HOURS": [800.0],
            }
        )

        result = _assemble_output(alloc, demand)
        row = result.iloc[0]
        assert row["BASE_GAP"] == pytest.approx(200.0, abs=0.1)
        assert row["SCENARIO_GAP"] == pytest.approx(400.0, abs=0.1)
        assert row["SUPPLY_DELTA"] == pytest.approx(200.0, abs=0.1)


class TestRunScenarioIntegration:
    """End-to-end test with all data-access functions mocked."""

    def test_returns_expected_columns(
        self, supply_df, working_days_df, weights_df, demand_df
    ):
        with (
            patch("logic.scenario.get_supply", return_value=supply_df),
            patch("logic.scenario.get_working_days", return_value=working_days_df),
            patch("logic.scenario.get_demand_weight", return_value=weights_df),
            patch("logic.scenario.get_demand", return_value=demand_df),
        ):
            result = run_scenario(
                regions=["East"],
                adjustments={"East": 2},
                start_date=date(2025, 1, 1),
                end_date=date(2025, 2, 28),
                adjustment_start_date=date(2025, 2, 1),
                pct_decrease=0.15,
                vac_days_per_month=20 / 12,
                sick_days_per_month=8 / 12,
            )

        expected_cols = {
            "CCRID", "PROJECT_NAME", "REGION", "DATE",
            "BASE_SUPPLY", "SCENARIO_SUPPLY", "SUPPLY_DELTA",
            "DEMAND", "BASE_GAP", "SCENARIO_GAP", "NET_BACKLOG",
        }
        assert set(result.columns) == expected_cols
        assert not result.empty
