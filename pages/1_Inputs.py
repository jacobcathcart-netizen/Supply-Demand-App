"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.adjustments import adjustment_inputs
from components.branding import (
    GRAY_600,
    NAVY,
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
from data.snowflake import get_backlog, get_demand_weight, get_projects, get_regions_df

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
# TAB 1: Scenario Parameters
# ═══════════════════════════════════════════════════════════════════

with tab_params:
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        # ── Region selection (outside form so it updates immediately) ──
        section_header("🏷️ Scenario", "Name and region selection")
        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"],
            key="region_selector",
        )
        st.session_state["selected_regions"] = selected_regions

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

            # ── Scenario identity ─────────────────────────────
            scenario_name = st.text_input(
                "Scenario name",
                value=_saved("scenario_name", "Scenario 1"),
            )

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
                vac_days_per_year = st.number_input(
                    "Vacation days / year",
                    min_value=0,
                    max_value=365,
                    value=int(
                        round(
                            _saved("vac_days_per_month", DEFAULT_VAC_DAYS_PER_YEAR / 12) * 12
                        )
                    ),
                    step=1,
                )
            with a3:
                sick_days_per_year = st.number_input(
                    "Sick days / year",
                    min_value=0,
                    max_value=365,
                    value=int(
                        round(
                            _saved("sick_days_per_month", DEFAULT_SICK_DAYS_PER_YEAR / 12) * 12
                        )
                    ),
                    step=1,
                )

            # Convert to monthly for internal storage
            vac_days_per_month = vac_days_per_year / 12
            sick_days_per_month = sick_days_per_year / 12

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

            submitted = st.form_submit_button("💾  Save Inputs", width="stretch")

        # ── Validation ──────────────────────────────────────────────────

        if submitted:
            errors: list[str] = []
            if start_date > end_date:
                errors.append("Start date must be before end date.")
            if not st.session_state["selected_regions"]:
                errors.append("Select at least one region.")

            if errors:
                for msg in errors:
                    st.error(msg)
                st.stop()

            st.session_state.update(
                inputs_saved=True,
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
            st.toast("Inputs saved!", icon="✅")

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
                region_names = st.session_state["selected_regions"]
                if len(region_names) <= 3:
                    region_display = ", ".join(region_names)
                else:
                    region_display = ", ".join(region_names[:3]) + f" +{len(region_names) - 3}"
                r3, r4 = st.columns(2)
                r3.metric("Regions", region_display)
                adj_start = st.session_state.get("adjustment_start_date")
                r4.metric("Adj. Start", str(adj_start) if adj_start else "—")

            with st.container(border=True):
                r5, r6, r7 = st.columns(3)
                r5.metric("Non-Project", f"{s['pct_decrease'] * 100:.0f}%")
                r6.metric("Vacation", f"{s['vac_days_per_month'] * 12:.0f}d/yr")
                r7.metric("Sick", f"{s['sick_days_per_month'] * 12:.0f}d/yr")

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

    # ── Headcount adjustments (visible as soon as regions are selected) ──

    if selected_regions:
        st.divider()
        section_header(
            "📆 Headcount Adjustments",
            "Add or remove FTEs per region. Changes take effect from the start date below.",
        )

        with st.form("adjustments_form"):
            adj_col1, adj_col2 = st.columns([1, 3])
            with adj_col1:
                adjustment_start_date = st.date_input(
                    "Adjustment start date",
                    value=st.session_state["adjustment_start_date"]
                    or _saved("start_date", DEFAULT_START_DATE),
                    format="MM/DD/YYYY",
                    help="Month from which headcount changes take effect",
                )

            adjustments = adjustment_inputs(
                selected_regions,
                st.session_state["adjustments"],
            )

            adj_submitted = st.form_submit_button(
                "💾  Save Adjustments", width="stretch"
            )

        if adj_submitted:
            st.session_state["adjustment_start_date"] = adjustment_start_date.replace(
                day=1
            )
            st.session_state["adjustments"] = adjustments
            st.toast("Adjustments saved!", icon="✅")

        # ── Run button ──────────────────────────────────────────────────

        _, center, _ = st.columns([1, 2, 1])
        with center:
            run = st.button("▶  Run Scenario", type="primary", width="stretch")

        if run:
            if not st.session_state["inputs_saved"]:
                st.warning("Save your inputs first before running the scenario.")
            else:
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

    section_header("Remove Projects", "Excluded projects are removed from demand and supply allocation")

    if not projects_df.empty and "CCRID" in projects_df.columns:
        # Only show projects that exist in the demand weights dataset
        try:
            weights_df = get_demand_weight()
            dataset_ccrids = set(weights_df["CCRID"].unique())
        except Exception:
            dataset_ccrids = set(projects_df["CCRID"].unique())

        in_dataset = projects_df[projects_df["CCRID"].isin(dataset_ccrids)].copy()

        if in_dataset.empty:
            st.info("No projects found in the current dataset.")
        else:
            # Dimension filters to narrow the list
            filter_cols = st.columns(3)
            with filter_cols[0]:
                region_opts = sorted(in_dataset["REGION"].dropna().unique().tolist())
                filter_region = st.multiselect(
                    "Filter by Region", options=region_opts, placeholder="All regions"
                )
            with filter_cols[1]:
                customer_opts = sorted(in_dataset["CUSTOMER"].dropna().unique().tolist())
                filter_customer = st.multiselect(
                    "Filter by Customer", options=customer_opts, placeholder="All customers"
                )
            with filter_cols[2]:
                state_opts = sorted(in_dataset["STATE"].dropna().unique().tolist())
                filter_state = st.multiselect(
                    "Filter by State", options=state_opts, placeholder="All states"
                )

            filtered_projects = in_dataset
            if filter_region:
                filtered_projects = filtered_projects[
                    filtered_projects["REGION"].isin(filter_region)
                ]
            if filter_customer:
                filtered_projects = filtered_projects[
                    filtered_projects["CUSTOMER"].isin(filter_customer)
                ]
            if filter_state:
                filtered_projects = filtered_projects[
                    filtered_projects["STATE"].isin(filter_state)
                ]

            project_options = (
                filtered_projects[["CCRID", "PROJECT_NAME"]]
                .drop_duplicates(subset="CCRID")
                .sort_values("PROJECT_NAME")
            )
            ccrid_to_label = dict(
                zip(
                    project_options["CCRID"],
                    project_options["PROJECT_NAME"] + " (" + project_options["CCRID"] + ")",
                )
            )

            # Keep previously excluded CCRIDs that are still valid
            valid_defaults = [
                c for c in st.session_state["excluded_ccrids"] if c in dataset_ccrids
            ]
            excluded = st.multiselect(
                "Exclude projects",
                options=list(ccrid_to_label.keys()),
                format_func=lambda c: ccrid_to_label.get(c, c),
                default=[c for c in valid_defaults if c in ccrid_to_label],
                placeholder="Select projects to exclude...",
            )
            st.session_state["excluded_ccrids"] = excluded

            st.caption(f"{len(project_options)} project(s) shown after filters")
    else:
        st.info("No project data available for exclusion.")

    st.divider()

    # ── Add custom projects ──────────────────────────────────────────

    section_header(
        "Add Projects",
        "Add hypothetical demand-only projects. Hours are spread evenly across scenario months from the start date.",
    )

    add_mode = st.radio(
        "Input method",
        ["Manual Entry", "CSV Upload"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if add_mode == "Manual Entry":
        with st.form("add_project_form", clear_on_submit=True):
            p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
            with p1:
                new_name = st.text_input("Project Name")
            with p2:
                new_region = st.selectbox("Region", options=regions_list)
            with p3:
                new_hours = st.number_input(
                    "Total Hours", min_value=0, value=0, step=100
                )
            with p4:
                new_start = st.date_input(
                    "Start Date",
                    value=_saved("start_date", DEFAULT_START_DATE),
                    format="MM/DD/YYYY",
                )
            add_submitted = st.form_submit_button("Add Project", width="stretch")

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
                        "START_DATE": str(new_start),
                    }
                )
                st.toast(f"Added project: {new_name.strip()}", icon="✅")
                st.rerun()

    else:  # CSV Upload
        st.caption(
            "CSV must contain columns: CCRID, PROJECT_NAME, REGION, "
            "TOTAL_HOURS, START_DATE (YYYY-MM-DD). One row per project."
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="project_csv")
        if uploaded is not None:
            try:
                csv_df = pd.read_csv(uploaded)
                required_cols = {"CCRID", "PROJECT_NAME", "REGION", "TOTAL_HOURS", "START_DATE"}
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
        st.divider()
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
