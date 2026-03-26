"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import pandas as pd
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
from data.snowflake import get_backlog, get_projects, get_regions_df

st.set_page_config(
    page_title="Inputs | CCR",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_branding()

st.title("Scenario Inputs")

# ── Session-state defaults ──────────────────────────────────────────

_DEFAULTS: dict[str, object] = {
    "scenario": {},
    "selected_regions": [],
    "adjustments": {},
    "inputs_saved": False,
    "adjustment_start_date": None,
    "excluded_ccrids": [],
    "custom_projects": [],
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


# ── Tabbed layout ───────────────────────────────────────────────────

tab_params, tab_projects = st.tabs(["Scenario Parameters", "Projects"])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: Scenario Parameters (existing content)
# ═══════════════════════════════════════════════════════════════════

with tab_params:
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
            submitted = st.form_submit_button("💾  Save Inputs", width="stretch")

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

            with st.container(border=True):
                r10, r11 = st.columns(2)
                r10.metric("Excluded Projects", len(st.session_state["excluded_ccrids"]))
                r11.metric("Custom Projects", len(st.session_state["custom_projects"]))

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
            run = st.button("▶  Run Scenario", type="primary", width="stretch")

        if run:
            st.switch_page("pages/2_Results.py")

# ═══════════════════════════════════════════════════════════════════
# TAB 2: Projects (add / remove)
# ═══════════════════════════════════════════════════════════════════

with tab_projects:
    section_header("Manage Projects", "Exclude existing projects or add custom ones")

    # ── Load project dimension table ─────────────────────────────────

    try:
        projects_df = get_projects()
    except Exception as exc:
        st.warning(f"Could not load project list: {exc}")
        projects_df = pd.DataFrame()

    # ── Remove existing projects ─────────────────────────────────────

    st.markdown(
        f"""
        <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                    font-size:1rem;margin:1rem 0 0.5rem;">
            Remove Projects
        </div>
        <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;
                    margin-bottom:0.75rem;">
            Excluded projects are removed from both demand and supply allocation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not projects_df.empty and "CCRID" in projects_df.columns:
        project_options = (
            projects_df[["CCRID", "PROJECT_NAME"]]
            .drop_duplicates(subset="CCRID")
            .sort_values("PROJECT_NAME")
        )
        ccrid_to_label = dict(
            zip(
                project_options["CCRID"],
                project_options["PROJECT_NAME"] + " (" + project_options["CCRID"] + ")",
            )
        )
        excluded = st.multiselect(
            "Exclude projects",
            options=list(ccrid_to_label.keys()),
            format_func=lambda c: ccrid_to_label.get(c, c),
            default=st.session_state["excluded_ccrids"],
            placeholder="Select projects to exclude...",
        )
        st.session_state["excluded_ccrids"] = excluded
    else:
        st.info("No project data available for exclusion.")

    st.divider()

    # ── Add custom projects ──────────────────────────────────────────

    st.markdown(
        f"""
        <div style="font-weight:600;color:{NAVY};font-family:Tahoma,sans-serif;
                    font-size:1rem;margin:0 0 0.5rem;">
            Add Projects
        </div>
        <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;
                    margin-bottom:0.75rem;">
            Add hypothetical projects with custom demand. Total hours are spread
            evenly across scenario months. Custom projects have zero supply
            (demand-only).
        </div>
        """,
        unsafe_allow_html=True,
    )

    add_manual, add_csv = st.tabs(["Manual Entry", "CSV Upload"])

    with add_manual:
        with st.form("add_project_form", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            with p1:
                new_name = st.text_input("Project Name")
            with p2:
                new_region = st.selectbox("Region", options=regions_list)
            with p3:
                new_hours = st.number_input(
                    "Total Hours", min_value=0, value=0, step=100
                )
            add_submitted = st.form_submit_button(
                "Add Project", width="stretch"
            )

        if add_submitted:
            if not new_name.strip():
                st.error("Project name is required.")
            else:
                counter = len(st.session_state["custom_projects"]) + 1
                st.session_state["custom_projects"].append(
                    {
                        "CCRID": f"CUSTOM_{counter:03d}",
                        "PROJECT_NAME": new_name.strip(),
                        "REGION": new_region,
                        "TOTAL_HOURS": new_hours,
                    }
                )
                st.toast(f"Added project: {new_name.strip()}", icon="✅")
                st.rerun()

    with add_csv:
        st.markdown(
            f"""
            <div style="color:{GRAY_600};font-size:0.85rem;font-family:Tahoma,sans-serif;
                        margin-bottom:0.5rem;">
                CSV must contain columns: <strong>CCRID</strong>, <strong>PROJECT_NAME</strong>,
                <strong>REGION</strong>, <strong>TOTAL_HOURS</strong> (one row per project).
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="project_csv")
        if uploaded is not None:
            try:
                csv_df = pd.read_csv(uploaded)
                required_cols = {"CCRID", "PROJECT_NAME", "REGION", "TOTAL_HOURS"}
                missing = required_cols - set(csv_df.columns)
                if missing:
                    st.error(f"CSV is missing columns: {', '.join(sorted(missing))}")
                else:
                    invalid_regions = set(csv_df["REGION"]) - set(regions_list)
                    if invalid_regions:
                        st.warning(
                            f"Rows with unknown regions will be skipped: "
                            f"{', '.join(sorted(invalid_regions))}"
                        )
                        csv_df = csv_df[csv_df["REGION"].isin(regions_list)]

                    if csv_df.empty:
                        st.warning("No valid rows to add after filtering.")
                    else:
                        new_projects = csv_df[list(required_cols)].to_dict("records")
                        existing_ccrids = {
                            p["CCRID"] for p in st.session_state["custom_projects"]
                        }
                        dupes = [p for p in new_projects if p["CCRID"] in existing_ccrids]
                        unique = [p for p in new_projects if p["CCRID"] not in existing_ccrids]

                        if dupes:
                            st.warning(
                                f"Skipped {len(dupes)} project(s) with duplicate CCRIDs."
                            )
                        if unique:
                            st.session_state["custom_projects"].extend(unique)
                            st.success(f"Added {len(unique)} project(s) from CSV.")
                            st.rerun()
            except Exception as exc:
                st.error(f"Failed to read CSV: {exc}")

    # ── Current custom projects table ────────────────────────────────

    if st.session_state["custom_projects"]:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_header(
            "Custom Projects",
            f"{len(st.session_state['custom_projects'])} project(s) added",
        )
        st.dataframe(
            pd.DataFrame(st.session_state["custom_projects"]),
            hide_index=True,
            width="stretch",
        )
        if st.button("Clear All Custom Projects"):
            st.session_state["custom_projects"] = []
            st.rerun()
