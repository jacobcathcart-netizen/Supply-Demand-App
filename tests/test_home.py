"""Smoke test for config module (no Snowflake connection required)."""

from config import (
    CACHE_TTL_SECONDS,
    DEFAULT_CM_HOURS,
    DEFAULT_PM_HOURS,
    DEFAULT_PRODUCTIVITY_LOSS,
    HOURS_PER_DAY,
    SESSION_DEFAULTS,
    SNOWFLAKE_SCHEMA,
)


def test_constants_are_sane():
    assert HOURS_PER_DAY == 8
    assert CACHE_TTL_SECONDS > 0
    assert 0 < DEFAULT_PRODUCTIVITY_LOSS < 1
    assert DEFAULT_PM_HOURS > 0
    assert DEFAULT_CM_HOURS > 0
    assert "." in SNOWFLAKE_SCHEMA


def test_session_defaults():
    assert SESSION_DEFAULTS.inputs_saved is False
    assert SESSION_DEFAULTS.adjustment_start_date is None
    assert isinstance(SESSION_DEFAULTS.scenario, dict)
