"""Sensitivity engine: run low/high variants of each input parameter.

Each parameter is varied independently (one-at-a-time) while all others
stay at their base values.  The results are used to build envelope and
tornado visualisations on the Results page.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import numpy as np
import pandas as pd

from components.visuals import _monthly_totals


# ── Parameter definitions ────────────────────────────────────────────


@dataclass(frozen=True)
class SensitivityParam:
    """Describes one input axis that can be varied."""

    name: str
    key: str  # kwarg name in run_scenario / _run
    delta_key: str  # key in the sensitivity config dict
    floor: float = 0.0
    ceiling: float = float("inf")
    is_headcount: bool = False
    is_backlog_only: bool = False  # CM/PM hours — only changes starting backlog
    is_date_shift: bool = False  # adjustment month offset
    unit: str = ""


PARAMS: list[SensitivityParam] = [
    SensitivityParam(
        name="Non-project %",
        key="pct_decrease",
        delta_key="pct_decrease_delta",
        floor=0.0,
        ceiling=1.0,
        unit="pp",
    ),
    SensitivityParam(
        name="Vacation days",
        key="vac_days_per_month",
        delta_key="vac_days_delta",
        floor=0.0,
        unit="d/yr",
    ),
    SensitivityParam(
        name="Sick days",
        key="sick_days_per_month",
        delta_key="sick_days_delta",
        floor=0.0,
        unit="d/yr",
    ),
    SensitivityParam(
        name="Headcount adj.",
        key="adjustments",
        delta_key="headcount_delta",
        is_headcount=True,
        unit="FTE",
    ),
    SensitivityParam(
        name="CM hours/item",
        key="cm_assumption",
        delta_key="cm_assumption_delta",
        floor=0.0,
        is_backlog_only=True,
        unit="hrs",
    ),
    SensitivityParam(
        name="PM hours/item",
        key="pm_assumption",
        delta_key="pm_assumption_delta",
        floor=0.0,
        is_backlog_only=True,
        unit="hrs",
    ),
    SensitivityParam(
        name="Adj. month",
        key="adjustment_start_date",
        delta_key="adj_months_delta",
        is_date_shift=True,
        unit="mo",
    ),
]


def _offset_month(d: date, months: int) -> date:
    """Shift a date by *months* months, clamping to the 1st of the month."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


# ── Public API ───────────────────────────────────────────────────────


@dataclass
class ParamResult:
    """Result of varying a single parameter."""

    name: str
    unit: str
    base_value: float
    low_value: float
    high_value: float
    low_monthly: pd.DataFrame
    high_monthly: pd.DataFrame
    low_ending_backlog: float
    high_ending_backlog: float


@dataclass
class SensitivityResult:
    """Full sensitivity analysis output."""

    base_monthly: pd.DataFrame
    base_ending_backlog: float
    param_results: list[ParamResult]
    envelope_min: pd.Series
    envelope_max: pd.Series


def run_sensitivity(
    *,
    base_kwargs: dict,
    sensitivity_config: dict,
    base_backlog: float,
    base_df: pd.DataFrame,
    run_fn: Callable[..., pd.DataFrame],
    backlog_fn: Callable[[int, int], float],
) -> SensitivityResult:
    """Run one-at-a-time sensitivity analysis.

    Parameters
    ----------
    base_kwargs:
        The keyword arguments used for the base ``_run()`` call (already
        converted to hashable types where needed).
    sensitivity_config:
        The ``scenario["sensitivity"]`` dict from session state.
    base_backlog:
        Starting backlog hours for the base case.
    base_df:
        The base-case scenario DataFrame (already computed).
    run_fn:
        Callable that mirrors the cached ``_run()`` wrapper on the
        Results page.  Accepts the same kwargs as ``base_kwargs``.
    backlog_fn:
        ``Callable(pm_hours, cm_hours) -> float`` that returns the
        initial backlog for a given PM/CM assumption pair.
    """
    base_monthly = _monthly_totals(base_df, backlog=base_backlog)
    base_ending = float(base_monthly["SCENARIO_GAP_CUMSUM"].iloc[-1]) if not base_monthly.empty else 0.0

    param_results: list[ParamResult] = []
    all_backlogs: list[pd.Series] = [base_monthly["SCENARIO_GAP_CUMSUM"]]

    for param in PARAMS:
        delta = sensitivity_config.get(param.delta_key, 0)
        if not delta:
            continue

        if param.is_backlog_only:
            # CM/PM hours: vary the backlog seed, keep the same scenario DF
            base_val = base_kwargs.get(param.key, 0)
            # For backlog-only params the base_kwargs won't have these keys
            # directly — they come from scenario_inputs on the Results page.
            low_val = max(base_val - delta, param.floor)
            high_val = min(base_val + delta, param.ceiling) if param.ceiling < float("inf") else base_val + delta

            if param.key == "cm_assumption":
                low_backlog = backlog_fn(base_kwargs.get("pm_assumption", 10), int(low_val))
                high_backlog = backlog_fn(base_kwargs.get("pm_assumption", 10), int(high_val))
            else:  # pm_assumption
                low_backlog = backlog_fn(int(low_val), base_kwargs.get("cm_assumption", 14))
                high_backlog = backlog_fn(int(high_val), base_kwargs.get("cm_assumption", 14))

            low_monthly = _monthly_totals(base_df, backlog=low_backlog)
            high_monthly = _monthly_totals(base_df, backlog=high_backlog)

        elif param.is_headcount:
            # Vary every region's adjustment by ±delta
            base_adj = dict(base_kwargs["adjustments"])
            low_adj = {r: v - delta for r, v in base_adj.items()}
            high_adj = {r: v + delta for r, v in base_adj.items()}

            low_kw = {**base_kwargs, "adjustments": low_adj}
            high_kw = {**base_kwargs, "adjustments": high_adj}
            low_df = run_fn(**low_kw)
            high_df = run_fn(**high_kw)
            low_monthly = _monthly_totals(low_df, backlog=base_backlog)
            high_monthly = _monthly_totals(high_df, backlog=base_backlog)

            # For display: show the per-region average adjustment as base_value
            adj_vals = list(base_adj.values())
            base_val = sum(adj_vals) / len(adj_vals) if adj_vals else 0
            low_val = base_val - delta
            high_val = base_val + delta

        elif param.is_date_shift:
            # Shift adjustment_start_date by ±delta months
            base_date = base_kwargs["adjustment_start_date"]
            start_date = base_kwargs["start_date"]
            end_date = base_kwargs["end_date"]
            low_date = max(_offset_month(base_date, -int(delta)), start_date)
            high_date = min(_offset_month(base_date, int(delta)), end_date)

            low_kw = {**base_kwargs, "adjustment_start_date": low_date}
            high_kw = {**base_kwargs, "adjustment_start_date": high_date}
            low_df = run_fn(**low_kw)
            high_df = run_fn(**high_kw)
            low_monthly = _monthly_totals(low_df, backlog=base_backlog)
            high_monthly = _monthly_totals(high_df, backlog=base_backlog)

            base_val = 0  # base is the reference point (no shift)
            low_val = -int(delta)
            high_val = int(delta)

        else:
            # Standard numeric parameter
            base_val = base_kwargs[param.key]
            low_val = max(base_val - delta, param.floor)
            high_val = min(base_val + delta, param.ceiling) if param.ceiling < float("inf") else base_val + delta

            low_kw = {**base_kwargs, param.key: low_val}
            high_kw = {**base_kwargs, param.key: high_val}
            low_df = run_fn(**low_kw)
            high_df = run_fn(**high_kw)
            low_monthly = _monthly_totals(low_df, backlog=base_backlog)
            high_monthly = _monthly_totals(high_df, backlog=base_backlog)

        low_ending = float(low_monthly["SCENARIO_GAP_CUMSUM"].iloc[-1]) if not low_monthly.empty else 0.0
        high_ending = float(high_monthly["SCENARIO_GAP_CUMSUM"].iloc[-1]) if not high_monthly.empty else 0.0

        param_results.append(
            ParamResult(
                name=param.name,
                unit=param.unit,
                base_value=base_val,
                low_value=low_val,
                high_value=high_val,
                low_monthly=low_monthly,
                high_monthly=high_monthly,
                low_ending_backlog=low_ending,
                high_ending_backlog=high_ending,
            )
        )

        all_backlogs.append(low_monthly["SCENARIO_GAP_CUMSUM"])
        all_backlogs.append(high_monthly["SCENARIO_GAP_CUMSUM"])

    # Build envelope across all scenarios (incremental min/max, no concat)
    envelope_min = all_backlogs[0].values.astype(float).copy()
    envelope_max = envelope_min.copy()
    for s in all_backlogs[1:]:
        vals = s.values.astype(float)
        np.minimum(envelope_min, vals, out=envelope_min)
        np.maximum(envelope_max, vals, out=envelope_max)
    envelope_min = pd.Series(envelope_min, index=base_monthly.index)
    envelope_max = pd.Series(envelope_max, index=base_monthly.index)

    return SensitivityResult(
        base_monthly=base_monthly,
        base_ending_backlog=base_ending,
        param_results=param_results,
        envelope_min=envelope_min,
        envelope_max=envelope_max,
    )
