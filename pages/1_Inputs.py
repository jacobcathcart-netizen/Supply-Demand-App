"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import streamlit as st

from components.adjustments import adjustment_inputs
from components.branding import apply_branding
from config import (
    DEFAULT_CM_HOURS,
    DEFAULT_END_DATE,
    DEFAULT_PCT_DECREASE,
    DEFAULT_PM_HOURS,
    DEFAULT_SICK_DAYS_PER_YEAR,
    DEFAULT_START_DATE,
    DEFAULT_VAC_DAYS_PER_YEAR,
)
from data.snowflake import get_backlog, get_regions_df

st.set_page_config(page_title="Inputs", layout="wide", initial_sidebar_state="expanded")
apply_branding()
st.title("Scenario Inputs")

# ── Session-state defaults ──────────────────────────────────────────

_DEFAULTS: dict[str, object] = {
    "scenario": {},
    "selected_regions": [],
    "adjustments": {},
    "inputs_saved": False,
    "adjustment_start_date": None,
}
for key, val in _DEFAULTS.items():
    st.session_state.setdefault(key, val)


# ── Region list (cached) ───────────────────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def _cached_regions() -> list[str]:
    df = get_regions_df()
    if df.empty or "REGION" not in df.columns:
        return []
    return df["REGION"].dropna().astype(str).sort_values().tolist()


regions_list = _cached_regions()

if not regions_list:
    st.error("Could not load regions from Snowflake.  Check connection on the Home page.")
    st.stop()

# ── Helper to read saved values with fallbacks ──────────────────────


def _saved(key: str, default: object = None) -> object:
    return st.session_state["scenario"].get(key, default)


# ── Layout ──────────────────────────────────────────────────────────
left, right = st.columns([1.2, 1])

with left:
    st.subheader("Scenario settings")
    with st.form("inputs_form"):
        scenario_name = st.text_input(
            "Scenario name",
            value=_saved("scenario_name", "Scenario 1"),
        )

        st.divider()

        start_date = st.date_input(
            "Start date",
            value=_saved("start_date", DEFAULT_START_DATE),
            format="MM/DD/YYYY",
        )
        end_date = st.date_input(
            "End date",
            value=_saved("end_date", DEFAULT_END_DATE),
            format="MM/DD/YYYY",
        )

        st.divider()

        pct_decrease = (
            st.number_input(
                "Non-project assumption (%)",
                min_value=0,
                max_value=100,
                value=int(_saved("pct_decrease", DEFAULT_PCT_DECREASE) * 100),
                step=1,
            ) / 100
        )

        vac_days_per_month = (
            st.number_input(
                "Vacation days per FTE per year",
                min_value=0,
                max_value=365,
                value=int(
                    round(
                        _saved("vac_days_per_month", DEFAULT_VAC_DAYS_PER_YEAR / 12) * 12
                    )
                ),
                step=1,
            ) / 12
        )

        sick_days_per_month = (
            st.number_input(
                "Sick days per FTE per year",
                min_value=0,
                max_value=365,
                value=int(
                    round(
                        _saved("sick_days_per_month", DEFAULT_SICK_DAYS_PER_YEAR / 12) * 12
                    )
                ),
                step=1,
            ) / 12
        )

        st.divider()

        cm_assumption = st.number_input(
            "Hours per CM backlog item",
            min_value=0,
            max_value=30,
            value=int(_saved("cm_assumption", DEFAULT_CM_HOURS)),
            step=1,
        )

        pm_assumption = st.number_input(
            "Hours per PM backlog item",
            min_value=0,
            max_value=30,
            value=int(_saved("pm_assumption", DEFAULT_PM_HOURS)),
            step=1,
        )

        st.divider()

        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"],
        )

        adjustment_start_date = st.date_input(
            "Headcount adjustment start date",
            value=st.session_state["adjustment_start_date"] or start_date,
            format="MM/DD/YYYY",
        )
        adjustment_start_date = adjustment_start_date.replace(day=1)

        submitted = st.form_submit_button("Save inputs")

    # ── Validation ──────────────────────────────────────────────────

    if submitted:
        errors: list[str] = []
        if start_date > end_date:
            errors.append("Start date must be before end date.")
        if adjustment_start_date < start_date or adjustment_start_date > end_date:
            errors.append("Adjustment start date must fall within the scenario range.")
        if not selected_regions:
            errors.append("Select at least one region.")

        if errors:
            for msg in errors:
                st.error(msg)
            st.stop()

        st.session_state.update(
            inputs_saved=True,
            selected_regions=selected_regions,
            adjustment_start_date=adjustment_start_date,
            scenario={
                "scenario_name": scenario_name,
                "pct_decrease": pct_decrease,
                "vac_days_per_month": vac_days_per_month,
                "sick_days_per_month": sick_days_per_month,
                "start_date": start_date,
                "end_date": end_date,
                "pm_assumption": pm_assumption,
                "cm_assumption": cm_assumption,
            },
        )
        st.success("Inputs saved.")


# ── Summary panel ───────────────────────────────────────────────────

with right:
    st.subheader("Scenario summary")

    if not st.session_state["inputs_saved"]:
        st.info("Save inputs to enable adjustments and results.")
    else:
        s = st.session_state["scenario"]
        st.json(
            {
                "Scenario Name": s["scenario_name"],
                "Start Date": str(s["start_date"]),
                "End Date": str(s["end_date"]),
                "Adjustment Start": str(st.session_state["adjustment_start_date"]),
                "Regions Selected": len(st.session_state["selected_regions"]),
                "Non-Project %": f"{s['pct_decrease'] * 100:.0f}%",
                "Vacation Days / Month": round(s["vac_days_per_month"], 2),
                "Sick Days / Month": round(s["sick_days_per_month"], 2),
                "Hours / PM Backlog": s["pm_assumption"],
                "Hours / CM Backlog": s["cm_assumption"],
            }
        )

# ── Backlog preview & adjustments ───────────────────────────────────

st.divider()

try:
    st.dataframe(get_backlog(pm_assumption, cm_assumption))
except Exception as exc:
    st.warning(f"Could not load backlog data: {exc}")

if st.session_state["inputs_saved"]:
    adjustments = adjustment_inputs(
        st.session_state["selected_regions"],
        st.session_state["adjustments"],
    )
    st.session_state["adjustments"] = adjustments

    c1, c2 = st.columns([1, 3])
    with c1:
        run = st.button("Run scenario", type="primary")
    with c2:
        st.caption("Runs the scenario and navigates to Results.")

    if run:
        st.switch_page("pages/2_Results.py")
