"""Smoke tests for the config module and data-layer imports."""

from __future__ import annotations

from datetime import date

from config import ScenarioInputs, DEFAULT_START_DATE, DEFAULT_END_DATE


class TestScenarioInputs:
    def test_defaults(self):
        s = ScenarioInputs()
        assert s.start_date == DEFAULT_START_DATE
        assert s.end_date == DEFAULT_END_DATE
        assert s.adjustment_start_date == s.start_date

    def test_immutable(self):
        s = ScenarioInputs()
        with __import__("pytest").raises(AttributeError):
            s.scenario_name = "changed"  # type: ignore[misc]

    def test_custom_adjustment_start(self):
        s = ScenarioInputs(adjustment_start_date=date(2025, 6, 1))
        assert s.adjustment_start_date == date(2025, 6, 1)
