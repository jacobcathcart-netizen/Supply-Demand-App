"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import streamlit as st

from components.adjustments import adjustment_inputs
from components.branding import (
    GRAY_600,
    LIGHT_BLUE,
    NAVY,
    TEAL,
    apply_branding,
    section_header,
    status_badge,
)
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

st.set_page_config(
    page_title="Inputs | CCR",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_branding()

# ── Sidebar branding ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:0.5rem 0 1.5rem;">
            <div style="font-size:1.5rem;font-weight:700;color:white;
                        font-family:Tahoma,sans-serif;letter-spacing:-0.02em;">
                ⚡ CCR
            </div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.6);
                        font-family:Tahoma,sans-serif;margin-top:0.15rem;">
                Workforce Planning
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    st.error("Could not load regions from Snowflake. Check connection on the Home page.")
    st.stop()

# ── Helper to read saved values with fallbacks ──────────────────────


def _saved(key: str, default: object = None) -> object:
    return st.session_state["scenario"].get(key, default)


# ── Layout: two-column card design ──────────────────────────────────
left, right = st.columns([1.2, 1], gap="large")

with left:
    with st.form("inputs_form"):
        # ── Date range ────────────────────────────────────
        section_header("📅 Date Range", "Define the scenario time window")
        d1, d2 = st.columns(2)
        with d1:
            start_date = st.date_input(
                "Start date",
                value=_saved("start_date", DEFAULT_START_DATE),
                format="MM/DD/YYYY",
            )
        with d2:
            end_date = st.date_input(
                "End date",
                value=_saved("end_date", DEFAULT_END_DATE),
                format="MM/DD/YYYY",
            )

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

        # ── Scenario identity ─────────────────────────────
        section_header("🏷️ Scenario", "Name and region selection")
        scenario_name = st.text_input(
            "Scenario name",
            value=_saved("scenario_name", "Scenario 1"),
        )
        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"],
        )

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

        # ── Workforce assumptions ─────────────────────────
        section_header("👷 Workforce Assumptions", "Time-off and productivity factors")
        a1, a2, a3 = st.columns(3)
        with a1:
            pct_decrease = (
                st.number_input(
                    "Non-project (%)",
                    min_value=0,
                    max_value=100,
                    value=int(_saved("pct_decrease", DEFAULT_PCT_DECREASE) * 100),
                    step=1,
                    help="Percentage of time spent on non-project work",
                ) / 100
            )
        with a2:
            vac_days_per_month = (
                st.number_input(
                    "Vacation days / year",
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
        with a3:
            sick_days_per_month = (
                st.number_input(
                    "Sick days / year",
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

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

        # ── Backlog assumptions ───────────────────────────
        section_header("🔧 Backlog Assumptions", "Hours per maintenance item")
        b1, b2 = st.columns(2)
        with b1:
            cm_assumption = st.number_input(
                "Hours / CM item",
                min_value=0,
                max_value=30,
                value=int(_saved("cm_assumption", DEFAULT_CM_HOURS)),
                step=1,
            )
        with b2:
            pm_assumption = st.number_input(
                "Hours / PM item",
                min_value=0,
                max_value=30,
                value=int(_saved("pm_assumption", DEFAULT_PM_HOURS)),
                step=1,
            )

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

        # ── Adjustment start ──────────────────────────────
        section_header("📆 Adjustment Timing")
        adjustment_start_date = st.date_input(
            "Headcount adjustment start",
            value=st.session_state["adjustment_start_date"] or start_date,
            format="MM/DD/YYYY",
            help="Month from which headcount changes take effect",
        )
        adjustment_start_date = adjustment_start_date.replace(day=1)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾  Save Inputs", use_container_width=True)

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
        st.toast("✅ Inputs saved successfully!", icon="✅")


# ── Summary panel ───────────────────────────────────────────────────

with right:
    if not st.session_state["inputs_saved"]:
        st.markdown(
            f"""
            <div style="background:#F8F9FC;border:1px dashed #D9DDE5;border-radius:12px;
                        padding:3rem 2rem;text-align:center;margin-top:2rem;">
                <div style="font-size:2.5rem;margin-bottom:1rem;">📋</div>
                <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                            font-size:1.1rem;margin-bottom:0.5rem;">
                    No Scenario Configured
                </div>
                <div style="color:{GRAY_600};font-size:0.9rem;font-family:Tahoma,sans-serif;">
                    Fill in the form and click <strong>Save Inputs</strong> to get started.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        s = st.session_state["scenario"]
        section_header("Scenario Summary")
        st.markdown(
            f"""
            <div style="margin-bottom:1rem;">
                {status_badge(s['scenario_name'], NAVY)}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Summary as clean metric rows
        with st.container(border=True):
            r1, r2 = st.columns(2)
            r1.metric("Start Date", str(s["start_date"]))
            r2.metric("End Date", str(s["end_date"]))

        with st.container(border=True):
            r3, r4 = st.columns(2)
            r3.metric("Regions", str(len(st.session_state["selected_regions"])))
            r4.metric("Adj. Start", str(st.session_state["adjustment_start_date"]))

        with st.container(border=True):
            r5, r6, r7 = st.columns(3)
            r5.metric("Non-Project", f"{s['pct_decrease'] * 100:.0f}%")
            r6.metric("Vac / mo", f"{s['vac_days_per_month']:.1f}d")
            r7.metric("Sick / mo", f"{s['sick_days_per_month']:.1f}d")

        with st.container(border=True):
            r8, r9 = st.columns(2)
            r8.metric("Hours / PM", s["pm_assumption"])
            r9.metric("Hours / CM", s["cm_assumption"])

# ── Backlog preview ──────────────────────────────────────────────────

st.divider()

with st.expander("📦  Backlog Preview", expanded=False):
    try:
        backlog_preview = get_backlog(pm_assumption, cm_assumption)
        if backlog_preview.empty:
            st.info("No backlog data available.")
        else:
            st.dataframe(backlog_preview, hide_index=True)
    except Exception as exc:
        st.warning(f"Could not load backlog data: {exc}")

# ── Adjustments & run ────────────────────────────────────────────────

if st.session_state["inputs_saved"]:
    st.divider()
    adjustments = adjustment_inputs(
        st.session_state["selected_regions"],
        st.session_state["adjustments"],
    )
    st.session_state["adjustments"] = adjustments

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])
    with center:
        run = st.button("▶  Run Scenario", type="primary", use_container_width=True)

    if run:
        st.switch_page("pages/2_Results.py")
