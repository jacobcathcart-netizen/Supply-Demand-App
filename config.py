"""Application-wide constants and default scenario values."""

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Final

# ── Snowflake schema ────────────────────────────────────────────────
SNOWFLAKE_SCHEMA: Final[str] = "SA.SUPPLY_DEMAND"
CACHE_TTL_SECONDS: Final[int] = 1800  # 30 minutes

# ── Scenario defaults ───────────────────────────────────────────────
DEFAULT_START_DATE: Final[date] = date(2025, 1, 1)
DEFAULT_END_DATE: Final[date] = date(2025, 12, 31)
DEFAULT_PCT_DECREASE: Final[float] = 0.15
DEFAULT_VAC_DAYS_PER_YEAR: Final[int] = 20
DEFAULT_SICK_DAYS_PER_YEAR: Final[int] = 8
DEFAULT_CM_HOURS: Final[int] = 14
DEFAULT_PM_HOURS: Final[int] = 10
HOURS_PER_DAY: Final[int] = 8

# ── Sensitivity defaults (absolute deltas) ────────────────────────
SENSITIVITY_PCT_DECREASE: Final[int] = 5        # ±5 percentage points
SENSITIVITY_VAC_DAYS: Final[int] = 5            # ±5 days/year
SENSITIVITY_SICK_DAYS: Final[int] = 3           # ±3 days/year
SENSITIVITY_CM_HOURS: Final[int] = 4            # ±4 hrs
SENSITIVITY_PM_HOURS: Final[int] = 3            # ±3 hrs
SENSITIVITY_HEADCOUNT: Final[int] = 2           # ±2 per region

# ── Chart styling ───────────────────────────────────────────────────
CHART_FIGSIZE_WIDE: Final[tuple[int, int]] = (13, 5)
CHART_FIGSIZE_TALL: Final[tuple[int, int]] = (12, 7)
BAR_WIDTH_DAYS: Final[int] = 15

# ── Demo preset ────────────────────────────────────────────────────
DEMO_REGIONS: Final[list[str]] = ["NC - Central"]


def build_demo_preset() -> dict:
    """Generate a demo preset with randomised end date, adjustment timing, and headcount."""
    extra_months = random.randint(1, 10)
    end_year = DEFAULT_END_DATE.year + (DEFAULT_END_DATE.month + extra_months - 1) // 12
    end_month = (DEFAULT_END_DATE.month + extra_months - 1) % 12 + 1
    end_date = date(end_year, end_month, 1)

    # Random adjustment start: not the first or last month
    total_months = (end_date.year - DEFAULT_START_DATE.year) * 12 + (
        end_date.month - DEFAULT_START_DATE.month
    )
    adj_offset = random.randint(1, max(total_months - 1, 1))
    adj_year = DEFAULT_START_DATE.year + (DEFAULT_START_DATE.month + adj_offset - 1) // 12
    adj_month = (DEFAULT_START_DATE.month + adj_offset - 1) % 12 + 1
    adj_start = date(adj_year, adj_month, 1)

    adjustments = {r: random.randint(3, 17) for r in DEMO_REGIONS}

    return {
        "scenario": {
            "scenario_name": "Demo Scenario",
            "start_date": DEFAULT_START_DATE,
            "end_date": end_date,
            "pct_decrease": DEFAULT_PCT_DECREASE,
            "vac_days_per_month": DEFAULT_VAC_DAYS_PER_YEAR / 12,
            "sick_days_per_month": DEFAULT_SICK_DAYS_PER_YEAR / 12,
            "pm_assumption": DEFAULT_PM_HOURS,
            "cm_assumption": DEFAULT_CM_HOURS,
        },
        "selected_regions": list(DEMO_REGIONS),
        "adjustments": adjustments,
        "adjustment_start_date": adj_start,
        "excluded_ccrids": [],
        "custom_projects": [],
    }


@dataclass(frozen=True)
class ScenarioInputs:
    """Immutable container for all scenario parameters."""

    scenario_name: str = "Scenario 1"
    start_date: date = DEFAULT_START_DATE
    end_date: date = DEFAULT_END_DATE
    pct_decrease: float = DEFAULT_PCT_DECREASE
    vac_days_per_month: float = DEFAULT_VAC_DAYS_PER_YEAR / 12
    sick_days_per_month: float = DEFAULT_SICK_DAYS_PER_YEAR / 12
    pm_assumption: int = DEFAULT_PM_HOURS
    cm_assumption: int = DEFAULT_CM_HOURS
    selected_regions: tuple[str, ...] = field(default_factory=tuple)
    adjustment_start_date: date | None = None
    adjustments: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.adjustment_start_date is None:
            object.__setattr__(self, "adjustment_start_date", self.start_date)
