"""Unit tests for chart-building functions in components.visuals."""

from __future__ import annotations

import pandas as pd
import pytest

from components.visuals import (
    _monthly_totals,
    _padded_limits,
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    get_region_backlog,
    scenario_supply_demand_with_gap,
    supply_delta_chart,
)


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Minimal scenario output for two months."""
    return pd.DataFrame(
        {
            "DATE": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "BASE_SUPPLY": [1000.0, 1100.0],
            "SCENARIO_SUPPLY": [1200.0, 1300.0],
            "DEMAND": [800.0, 900.0],
            "BASE_GAP": [200.0, 200.0],
            "SCENARIO_GAP": [400.0, 400.0],
            "SUPPLY_DELTA": [200.0, 200.0],
        }
    )


class TestGetRegionBacklog:
    def test_returns_value_when_present(self):
        df = pd.DataFrame({"Region": ["East"], "HOUR_BACKLOG": [123.4]})
        assert get_region_backlog(df, "East") == 123.4

    def test_returns_zero_when_missing(self):
        df = pd.DataFrame({"Region": ["East"], "HOUR_BACKLOG": [123.4]})
        assert get_region_backlog(df, "West") == 0.0


class TestMonthlyTotals:
    def test_empty_input_returns_empty(self):
        assert _monthly_totals(pd.DataFrame()).empty

    def test_cumsum_includes_backlog_seed(self, sample_df):
        result = _monthly_totals(sample_df, backlog=500)
        assert result["SCENARIO_GAP_CUMSUM"].iloc[0] == pytest.approx(500 + (-400), abs=1)


class TestPaddedLimits:
    def test_symmetric_padding(self):
        s = pd.Series([-100, 200])
        lo, hi = _padded_limits(s, padding_frac=0.1, min_pad=1)
        assert lo < -100
        assert hi > 200


class TestChartFunctions:
    """Ensure every chart function returns a Figure or None."""

    @pytest.mark.parametrize(
        "chart_fn",
        [
            baseline_supply_demand_with_gap,
            scenario_supply_demand_with_gap,
        ],
    )
    def test_line_charts_return_figure(self, sample_df, chart_fn):
        fig = chart_fn(sample_df, region_label="Test")
        assert fig is not None

    def test_gap_bar_chart_returns_figure(self, sample_df):
        fig = gap_bar_chart(sample_df, region_label="Test", backlog=100)
        assert fig is not None

    def test_backlog_trend_chart_returns_figure(self, sample_df):
        fig = backlog_trend_chart(sample_df, region_label="Test", backlog=100)
        assert fig is not None

    def test_legacy_supply_delta_chart(self, sample_df):
        fig = supply_delta_chart(sample_df, region_label="Test", backlog=100)
        assert fig is not None

    def test_empty_df_returns_none(self):
        empty = pd.DataFrame()
        assert baseline_supply_demand_with_gap(empty) is None
        assert gap_bar_chart(empty) is None
        assert backlog_trend_chart(empty) is None
