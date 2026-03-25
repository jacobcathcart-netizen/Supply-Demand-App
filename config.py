"""Centralised configuration for the Supply & Demand app."""

from dataclasses import dataclass
from datetime import date

# ── Snowflake ────────────────────────────────────────────────────────────────
SNOWFLAKE_SCHEMA = "SA.SUPPLY_DEMAND"
CACHE_TTL_SECONDS = 1800  # 30 minutes

# ── Scenario defaults ────────────────────────────────────────────────────────
DEFAULT_START_DATE = date(2025, 1, 1)
DEFAULT_END_DATE = date(2025, 12, 31)
DEFAULT_PRODUCTIVITY_LOSS = 0.15
DEFAULT_VACATION_DAYS_PER_YEAR = 20
DEFAULT_SICK_DAYS_PER_YEAR = 8
DEFAULT_PM_HOURS = 10
DEFAULT_CM_HOURS = 14
HOURS_PER_DAY = 8

# ── Chart layout ─────────────────────────────────────────────────────────────
CHART_FIGSIZE = (13, 5)
CHART_FIGSIZE_SMALL = (12, 5)
BAR_WIDTH_DAYS = 15

# ── Session-state keys ───────────────────────────────────────────────────────
SS_SCENARIO = "scenario"
SS_REGIONS = "selected_regions"
SS_ADJUSTMENTS = "adjustments"
SS_INPUTS_SAVED = "inputs_saved"
SS_ADJ_START = "adjustment_start_date"


@dataclass(frozen=True)
class SessionDefaults:
    """Default values written into session state on first load."""

    scenario: dict
    selected_regions: list
    adjustments: dict
    inputs_saved: bool = False
    adjustment_start_date: date | None = None


SESSION_DEFAULTS = SessionDefaults(
    scenario={},
    selected_regions=[],
    adjustments={},
)
