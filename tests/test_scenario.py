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
    _recalculate_weights_from_demand,
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
        no_excl = pd.DataFrame(columns=["CCRID", "MONTH_NUMBER"])

        result = _assemble_output(alloc, demand, no_excl)
        row = result.iloc[0]
        assert row["BASE_GAP"] == pytest.approx(200.0, abs=0.1)
        assert row["SCENARIO_GAP"] == pytest.approx(400.0, abs=0.1)
        assert row["SUPPLY_DELTA"] == pytest.approx(200.0, abs=0.1)
        assert row["DEMAND"] == pytest.approx(800.0, abs=0.1)
        assert row["SCENARIO_DEMAND"] == pytest.approx(800.0, abs=0.1)


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
            "DEMAND", "SCENARIO_DEMAND", "BASE_GAP", "SCENARIO_GAP",
        }
        assert set(result.columns) == expected_cols
        assert not result.empty


class TestRecalculateWeightsFromDemand:
    """Weights should be recalculated as demand proportions per group."""

    def test_weights_sum_to_one_after_exclusion(self):
        weights = pd.DataFrame(
            {
                "CCRID": ["P001", "P002", "P003", "P001", "P002", "P003"],
                "REGION": ["East", "East", "East", "East", "East", "East"],
                "MONTH_NUMBER": [1, 1, 1, 2, 2, 2],
                "ALLOCATION": [0.5, 0.3, 0.2, 0.5, 0.3, 0.2],
            }
        )
        demand = pd.DataFrame(
            {
                "CCRID": ["P001", "P002", "P003", "P001", "P002", "P003"],
                "MONTH_NUMBER": [1, 1, 1, 2, 2, 2],
                "DEMAND_HOURS": [500, 300, 200, 500, 300, 200],
            }
        )
        # Exclude P003 then recalculate
        filtered_w = weights[~weights["CCRID"].isin(["P003"])]
        filtered_d = demand[~demand["CCRID"].isin(["P003"])]
        result = _recalculate_weights_from_demand(filtered_w, filtered_d)

        for _, group in result.groupby(["REGION", "MONTH_NUMBER"]):
            assert group["ALLOCATION"].sum() == pytest.approx(1.0)

        # P001 demand=500, P002 demand=300 → P001 weight = 500/800 = 0.625
        p001_m1 = result[(result["CCRID"] == "P001") & (result["MONTH_NUMBER"] == 1)]
        assert p001_m1["ALLOCATION"].iloc[0] == pytest.approx(0.625)

    def test_no_change_when_all_projects_included(self):
        weights = pd.DataFrame(
            {
                "CCRID": ["P001", "P002"],
                "REGION": ["East", "East"],
                "MONTH_NUMBER": [1, 1],
                "ALLOCATION": [0.6, 0.4],
            }
        )
        demand = pd.DataFrame(
            {
                "CCRID": ["P001", "P002"],
                "MONTH_NUMBER": [1, 1],
                "DEMAND_HOURS": [600, 400],
            }
        )
        result = _recalculate_weights_from_demand(weights, demand)
        assert result["ALLOCATION"].tolist() == pytest.approx([0.6, 0.4])


class TestExclusionPreservesBaseline:
    """Excluding a project must not change baseline supply, demand, or total
    scenario supply.  Excluded project-months get SCENARIO_SUPPLY = 0 and
    SCENARIO_DEMAND = 0 while retaining their baseline values."""

    _supply_df = pd.DataFrame(
        {
            "REGION": ["East", "East"],
            "MONTH_NUMBER": [1, 2],
            "COUNT": [10, 10],
        }
    )
    _working_days_df = pd.DataFrame(
        {
            "MONTH_START": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "BUSINESS_DAYS": [22, 20],
        }
    )
    _weights_df = pd.DataFrame(
        {
            "SERVICE_REGION_ST": ["East", "East", "East", "East"],
            "CCRID": ["P001", "P002", "P001", "P002"],
            "MONTH_NUMBER": [1, 1, 2, 2],
            "ALLOCATION": [0.6, 0.4, 0.6, 0.4],
        }
    )
    _demand_df = pd.DataFrame(
        {
            "CCRID": ["P001", "P001", "P002", "P002"],
            "PROJECT_NAME": ["Alpha", "Alpha", "Beta", "Beta"],
            "MONTH_NUMBER": [1, 2, 1, 2],
            "HOURS": [600, 600, 400, 400],
        }
    )
    _common_kwargs = dict(
        regions=["East"],
        adjustments={"East": 0},
        start_date=date(2025, 1, 1),
        end_date=date(2025, 2, 28),
        adjustment_start_date=date(2025, 1, 1),
        pct_decrease=0.15,
        vac_days_per_month=20 / 12,
        sick_days_per_month=8 / 12,
    )

    def _run(self, **extra_kwargs):
        with (
            patch("logic.scenario.get_supply", return_value=self._supply_df),
            patch("logic.scenario.get_working_days", return_value=self._working_days_df),
            patch("logic.scenario.get_demand_weight", return_value=self._weights_df),
            patch("logic.scenario.get_demand", return_value=self._demand_df),
        ):
            return run_scenario(**self._common_kwargs, **extra_kwargs)

    def test_baseline_supply_unchanged(self):
        result_all = self._run()
        result_excl = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-01-01"}],
        )
        assert result_all["BASE_SUPPLY"].sum() == pytest.approx(
            result_excl["BASE_SUPPLY"].sum(), abs=0.2
        )

    def test_baseline_demand_unchanged(self):
        result_all = self._run()
        result_excl = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-01-01"}],
        )
        assert result_all["DEMAND"].sum() == pytest.approx(
            result_excl["DEMAND"].sum(), abs=0.2
        )

    def test_scenario_supply_total_unchanged(self):
        result_all = self._run()
        result_excl = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-01-01"}],
        )
        assert result_all["SCENARIO_SUPPLY"].sum() == pytest.approx(
            result_excl["SCENARIO_SUPPLY"].sum(), abs=0.2
        )

    def test_excluded_project_has_zero_scenario(self):
        result = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-01-01"}],
        )
        p002 = result[result["CCRID"] == "P002"]
        assert len(p002) == 2  # still present in output
        assert p002["SCENARIO_SUPPLY"].sum() == 0
        assert p002["SCENARIO_DEMAND"].sum() == 0
        assert p002["BASE_SUPPLY"].sum() > 0  # baseline unaffected
        assert p002["DEMAND"].sum() > 0  # baseline demand retained

    def test_partial_date_exclusion(self):
        """Excluding P002 from month 2 keeps it active in month 1."""
        result = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-02-01"}],
        )
        p002 = result[result["CCRID"] == "P002"]
        assert len(p002) == 2  # present in both months

        m1 = p002[p002["DATE"].dt.month == 1].iloc[0]
        m2 = p002[p002["DATE"].dt.month == 2].iloc[0]

        # Month 1: normal scenario values
        assert m1["SCENARIO_SUPPLY"] > 0
        assert m1["SCENARIO_DEMAND"] > 0

        # Month 2: zeroed scenario values
        assert m2["SCENARIO_SUPPLY"] == 0
        assert m2["SCENARIO_DEMAND"] == 0
        assert m2["BASE_SUPPLY"] > 0  # baseline still present

    def test_mid_month_exclusion_date_truncated(self):
        """EXCLUDE_FROM mid-month should exclude that entire month."""
        result = self._run(
            excluded_projects=[{"CCRID": "P002", "EXCLUDE_FROM": "2025-01-15"}],
        )
        p002 = result[result["CCRID"] == "P002"]
        # January should be excluded (truncated to Jan 1)
        m1 = p002[p002["DATE"].dt.month == 1].iloc[0]
        assert m1["SCENARIO_SUPPLY"] == 0
        assert m1["SCENARIO_DEMAND"] == 0


class TestCustomProjectReceivesSupply:
    """Custom projects should participate in allocation and receive supply."""

    def test_custom_project_gets_proportional_supply(self):
        supply_df = pd.DataFrame(
            {
                "REGION": ["East", "East"],
                "MONTH_NUMBER": [1, 2],
                "COUNT": [10, 10],
            }
        )
        working_days_df = pd.DataFrame(
            {
                "MONTH_START": pd.to_datetime(["2025-01-01", "2025-02-01"]),
                "BUSINESS_DAYS": [22, 20],
            }
        )
        weights_df = pd.DataFrame(
            {
                "SERVICE_REGION_ST": ["East", "East"],
                "CCRID": ["P001", "P001"],
                "MONTH_NUMBER": [1, 2],
                "ALLOCATION": [1.0, 1.0],
            }
        )
        demand_df = pd.DataFrame(
            {
                "CCRID": ["P001", "P001"],
                "PROJECT_NAME": ["Alpha", "Alpha"],
                "MONTH_NUMBER": [1, 2],
                "HOURS": [500, 500],
            }
        )

        custom = [
            {
                "CCRID": "CUSTOM_001",
                "PROJECT_NAME": "NewProject",
                "REGION": "East",
                "TOTAL_HOURS": 1000,
                "START_DATE": "2025-01-01",
            }
        ]

        common_kwargs = dict(
            regions=["East"],
            adjustments={"East": 0},
            start_date=date(2025, 1, 1),
            end_date=date(2025, 2, 28),
            adjustment_start_date=date(2025, 1, 1),
            pct_decrease=0.0,
            vac_days_per_month=0,
            sick_days_per_month=0,
        )

        with (
            patch("logic.scenario.get_supply", return_value=supply_df),
            patch("logic.scenario.get_working_days", return_value=working_days_df),
            patch("logic.scenario.get_demand_weight", return_value=weights_df),
            patch("logic.scenario.get_demand", return_value=demand_df),
        ):
            result_base = run_scenario(**common_kwargs)
            result_custom = run_scenario(**common_kwargs, custom_projects=custom)

        # Total supply should be the same
        assert result_base["SCENARIO_SUPPLY"].sum() == pytest.approx(
            result_custom["SCENARIO_SUPPLY"].sum(), abs=0.2
        )

        # Custom project should have non-zero supply
        custom_rows = result_custom[result_custom["CCRID"] == "CUSTOM_001"]
        assert not custom_rows.empty
        assert custom_rows["SCENARIO_SUPPLY"].sum() > 0
