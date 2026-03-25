"""Inputs page — configure scenario parameters and headcount adjustments."""

import streamlit as st
from datetime import date

from config import (
    DEFAULT_CM_HOURS,
    DEFAULT_END_DATE,
    DEFAULT_PM_HOURS,
    DEFAULT_PRODUCTIVITY_LOSS,
    DEFAULT_SICK_DAYS_PER_YEAR,
    DEFAULT_START_DATE,
    DEFAULT_VACATION_DAYS_PER_YEAR,
    SS_ADJ_START,
    SS_ADJUSTMENTS,
    SS_INPUTS_SAVED,
    SS_REGIONS,
    SS_SCENARIO,
)
from data.snowflake import get_backlog, get_regions_df
from components.adjustments import adjustment_inputs

st.set_page_config(page_title="Inputs", layout="wide", initial_sidebar_state="expanded")
st.title("Scenario Inputs")

# ── Session-state defaults ───────────────────────────────────────────────────
for key, default in {
    SS_SCENARIO: {},
    SS_REGIONS: [],
    SS_ADJUSTMENTS: {},
    SS_INPUTS_SAVED: False,
    SS_ADJ_START: None,
}.items():
    st.session_state.setdefault(key, default)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_regions() -> list[str]:
    regions_df = get_regions_df()
    if regions_df.empty or "REGION" not in regions_df.columns:
        return []
    return regions_df["REGION"].dropna().astype(str).sort_values().tolist()


regions_list = cached_regions()

# ── Layout ───────────────────────────────────────────────────────────────────
left, right = st.columns([1.2, 1])

with left:
    st.subheader("Scenario settings")
    s = st.session_state[SS_SCENARIO]

    with st.form("inputs_form"):
        scenario_name = st.text_input(
            "Scenario name", value=s.get("scenario_name", "Scenario 1"),
        )

        st.divider()

        start_date = st.date_input(
            "Start Date",
            value=s.get("start_date", DEFAULT_START_DATE),
            format="MM/DD/YYYY",
        )
        end_date = st.date_input(
            "End Date",
            value=s.get("end_date", DEFAULT_END_DATE),
            format="MM/DD/YYYY",
        )

        st.divider()

        pct_decrease = (
            st.number_input(
                "Non-Project Assumption",
                min_value=0, max_value=100,
                value=int(s.get("pct_decrease", DEFAULT_PRODUCTIVITY_LOSS) * 100),
                step=1,
            ) / 100
        )

        vac_days_per_month = (
            st.number_input(
                "Vacation days per FTE per year",
                min_value=0, max_value=365,
                value=int(round(
                    s.get("vac_days_per_month", DEFAULT_VACATION_DAYS_PER_YEAR / 12) * 12
                )),
                step=1,
            ) / 12
        )

        sick_days_per_month = (
            st.number_input(
                "Sick days per FTE per year",
                min_value=0, max_value=365,
                value=int(round(
                    s.get("sick_days_per_month", DEFAULT_SICK_DAYS_PER_YEAR / 12) * 12
                )),
                step=1,
            ) / 12
        )

        st.divider()

        cm_assumption = st.number_input(
            "Hours Per CM Backlog",
            min_value=0, max_value=30,
            value=int(s.get("cm_assumption", DEFAULT_CM_HOURS)),
            step=1,
        )

        pm_assumption = st.number_input(
            "Hours Per PM Backlog",
            min_value=0, max_value=30,
            value=int(s.get("pm_assumption", DEFAULT_PM_HOURS)),
            step=1,
        )

        st.divider()

        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state[SS_REGIONS],
        )

        adjustment_start_date = st.date_input(
            "Headcount adjustment start date",
            value=st.session_state[SS_ADJ_START] or start_date,
            format="MM/DD/YYYY",
        )
        adjustment_start_date = adjustment_start_date.replace(day=1)

        submitted = st.form_submit_button("Save inputs")

    # ── Validation ───────────────────────────────────────────────────────────
    if submitted:
        if start_date > end_date:
            st.error("Start Date must be before End Date.")
            st.stop()

        if not (start_date <= adjustment_start_date <= end_date):
            st.error("Headcount adjustment start date must be within the scenario date range.")
            st.stop()

        if not selected_regions:
            st.error("Select at least one region.")
            st.stop()

        st.session_state[SS_INPUTS_SAVED] = True
        st.session_state[SS_REGIONS] = selected_regions
        st.session_state[SS_ADJ_START] = adjustment_start_date
        st.session_state[SS_SCENARIO] = {
            "scenario_name": scenario_name,
            "pct_decrease": pct_decrease,
            "vac_days_per_month": vac_days_per_month,
            "sick_days_per_month": sick_days_per_month,
            "start_date": start_date,
            "end_date": end_date,
            "pm_assumption": pm_assumption,
            "cm_assumption": cm_assumption,
        }
        st.success("Inputs saved.")

# ── Right column: summary ────────────────────────────────────────────────────
with right:
    st.subheader("Scenario summary")

    if not st.session_state[SS_INPUTS_SAVED]:
        st.info("Save inputs to enable adjustments and results.")
    else:
        s = st.session_state[SS_SCENARIO]
        st.json({
            "Scenario Name": s["scenario_name"],
            "Start Date": str(s["start_date"]),
            "End Date": str(s["end_date"]),
            "Adjustment Start": str(st.session_state[SS_ADJ_START]),
            "Regions Selected": len(st.session_state[SS_REGIONS]),
            "Productivity Decrease": f"{s['pct_decrease'] * 100:.0f}%",
            "Vacation Days per Month": round(s["vac_days_per_month"], 2),
            "Sick Days per Month": round(s["sick_days_per_month"], 2),
            "Hours Per PM Backlog": s["pm_assumption"],
            "Hours Per CM Backlog": s["cm_assumption"],
        })

# ── Backlog & adjustments ────────────────────────────────────────────────────
st.divider()
st.dataframe(get_backlog(pm_assumption, cm_assumption))

if st.session_state[SS_INPUTS_SAVED]:
    adjustments = adjustment_inputs(
        st.session_state[SS_REGIONS],
        st.session_state[SS_ADJUSTMENTS],
    )
    st.session_state[SS_ADJUSTMENTS] = adjustments

    c1, c2 = st.columns([1, 3])
    with c1:
        run = st.button("Run scenario", type="primary")
    with c2:
        st.caption("Runs the scenario and navigates to Results.")

    if run:
        st.switch_page("pages/2_Results.py")
