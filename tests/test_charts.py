"""Unit tests for the Plotly chart builders."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from components.charts import (
    _monthly_totals,
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    scenario_supply_demand_with_gap,
)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DATE": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "BASE_SUPPLY": [1000.0, 1200.0],
            "SCENARIO_SUPPLY": [1100.0, 1300.0],
            "DEMAND": [800.0, 900.0],
            "SCENARIO_DEMAND": [800.0, 900.0],
            "BASE_GAP": [200.0, 300.0],
            "SCENARIO_GAP": [300.0, 400.0],
            "SUPPLY_DELTA": [0.0, 100.0],
        }
    )


class TestMonthlyTotals:
    def test_returns_cumulative_backlog(self, sample_df):
        result = _monthly_totals(sample_df, backlog=500)
        assert "SCENARIO_GAP_CUMSUM" in result.columns
        assert len(result) == 2

    def test_empty_input(self):
        result = _monthly_totals(pd.DataFrame())
        assert result.empty


class TestBaselineChart:
    def test_returns_figure(self, sample_df):
        fig = baseline_supply_demand_with_gap(sample_df)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_returns_none_for_empty(self):
        assert baseline_supply_demand_with_gap(pd.DataFrame()) is None


class TestScenarioChart:
    def test_returns_figure(self, sample_df):
        fig = scenario_supply_demand_with_gap(sample_df)
        assert isinstance(fig, go.Figure)


class TestGapBarChart:
    def test_returns_figure(self, sample_df):
        fig = gap_bar_chart(sample_df)
        assert isinstance(fig, go.Figure)


class TestBacklogTrend:
    def test_returns_figure(self, sample_df):
        fig = backlog_trend_chart(sample_df, backlog=500)
        assert isinstance(fig, go.Figure)
