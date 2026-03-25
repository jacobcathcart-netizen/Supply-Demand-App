"""Application-wide constants and default scenario values."""

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

# ── Chart styling ───────────────────────────────────────────────────
CHART_FIGSIZE_WIDE: Final[tuple[int, int]] = (13, 5)
CHART_FIGSIZE_TALL: Final[tuple[int, int]] = (12, 7)
BAR_WIDTH_DAYS: Final[int] = 15


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
