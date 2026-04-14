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
    SWAT, 
)
from data.snowflake import (
    get_backlog,
    get_cm_backlog,
    get_demand_weight,
    get_pm_backlog,
    get_projects,
    get_regions_df,
)

st.set_page_config(
    page_title="Inputs | CCR",
    page_icon="assets/logo.jpg",
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
    "excluded_projects": [],
    "custom_projects": [],
    "swat_allocation": [],
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
    # ── Top row: scenario identity (outside form for immediate updates) ──
    id_left, id_right = st.columns(2)
    with id_left:
        scenario_name = st.text_input(
            "Scenario name",
            value=_saved("scenario_name", "Scenario 1"),
            key="scenario_name_input",
        )
    with id_right:
        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"],
            key="region_selector",
        )
        st.session_state["selected_regions"] = selected_regions

    # ── Single form: assumptions + adjustments side by side ──────────
    with st.form("scenario_form"):
        left, right = st.columns([1, 1], gap="large")

        with left:
            # Date range
            section_header("Date Range")
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

            # Workforce assumptions
            section_header("Workforce Assumptions")
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
            # Swat Allocation
            section_header("Swat Allocation")
            f1, = st.columns(1)
            with f1:
                swat_allocation = st.number_input(
                    "Swat Headcount",
                    min_value=0,
                    value=int(
                        round(
                            _saved("swat_allocation",SWAT)
                        )
                    ),
                    step=1
                )
            # Backlog assumptions
            section_header("Backlog Assumptions")
            
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

        with right:
            section_header("Headcount Adjustments")
            if selected_regions:
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
            else:
                adjustment_start_date = None
                adjustments = {}
                st.caption("Select at least one region above to configure adjustments.")

        submitted = st.form_submit_button("Save & Continue", type="primary", width="stretch")

    # ── Validation & save ────────────────────────────────────────────

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
                "swat_allocation": swat_allocation
            },
            adjustments=adjustments,
        )
        if adjustment_start_date is not None:
            st.session_state["adjustment_start_date"] = adjustment_start_date.replace(
                day=1
            )
        st.toast("Inputs saved!", icon="✅")

    # ── Run button ───────────────────────────────────────────────────

    _, center, _ = st.columns([1, 2, 1])
    with center:
        run = st.button("Run Scenario", type="primary", width="stretch")

    if run:
        if not st.session_state["inputs_saved"]:
            st.warning("Save your inputs first before running the scenario.")
        else:
            st.switch_page("pages/2_Results.py")

    # ── Backlog preview (collapsed) ──────────────────────────────────

    with st.expander("Backlog Preview", expanded=False):
        try:
            import matplotlib.pyplot as plt
            from components.branding import LIGHT_BLUE, NAVY, YELLOW, WARM_WHITE, GRAY

            backlog_preview = get_backlog(pm_assumption, cm_assumption)
            if not backlog_preview.empty:
                for col in ("COUNT", "HOURS"):
                    if col in backlog_preview.columns:
                        backlog_preview[col] = pd.to_numeric(backlog_preview[col], errors="coerce").fillna(0)
            if backlog_preview.empty:
                st.info("No backlog data available.")
            else:
                # ── Load PM / CM breakdown ────────────────────────
                pm_df = get_pm_backlog()
                cm_df = get_cm_backlog()
                pm_df["COUNT"] = pd.to_numeric(pm_df["COUNT"], errors="coerce").fillna(0)
                cm_df["COUNT"] = pd.to_numeric(cm_df["COUNT"], errors="coerce").fillna(0)
                pm_items = int(pm_df["COUNT"].sum())
                cm_items = int(cm_df["COUNT"].sum())
                pm_hours = pm_items * pm_assumption
                cm_hours = cm_items * cm_assumption

                # ── Summary metrics ───────────────────────────────
                total_items = int(backlog_preview["COUNT"].sum())
                total_hours = backlog_preview["HOURS"].sum()
                n_regions = backlog_preview["REGION"].nunique()
                n_projects = backlog_preview["CCRID"].nunique()

                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Total Jobs", f"{total_items:,}")
                m2.metric("Total Hours", f"{total_hours:,.0f}")
                m3.metric("PM Jobs", f"{pm_items:,}", delta=f"{pm_hours:,.0f} hrs")
                m4.metric("CM Jobs", f"{cm_items:,}", delta=f"{cm_hours:,.0f} hrs")
                m5.metric("Regions", f"{n_regions}")
                m6.metric("Projects", f"{n_projects}")

                # ── Charts: by-region bar + PM vs CM breakdown ────
                by_region = (
                    backlog_preview.groupby("REGION", as_index=False)
                    .agg(ITEMS=("COUNT", "sum"), HOURS=("HOURS", "sum"))
                    .sort_values("HOURS", ascending=True)
                )

                chart_left, chart_right = st.columns(2)

                with chart_left:
                    fig1, ax1 = plt.subplots(figsize=(6, max(3, len(by_region) * 0.4)))
                    ax1.barh(
                        by_region["REGION"], by_region["HOURS"],
                        color=LIGHT_BLUE, edgecolor="none", height=0.6,
                    )
                    for i, (hrs, region) in enumerate(
                        zip(by_region["HOURS"], by_region["REGION"])
                    ):
                        ax1.text(
                            hrs + total_hours * 0.01, i, f"{hrs:,.0f}",
                            va="center", fontsize=8, fontweight="bold", color=NAVY,
                        )
                    ax1.set_title("Backlog Hours by Region", fontsize=12, fontweight=600)
                    ax1.set_xlabel("")
                    ax1.spines["top"].set_visible(False)
                    ax1.spines["right"].set_visible(False)
                    ax1.spines["bottom"].set_visible(False)
                    ax1.tick_params(axis="x", labelbottom=False)
                    ax1.tick_params(axis="y", labelsize=9)
                    fig1.tight_layout()
                    st.pyplot(fig1, clear_figure=True)

                with chart_right:
                    try:
                        pm_by_region = (
                            pm_df.groupby("REGION", as_index=False)["COUNT"]
                            .sum()
                            .rename(columns={"COUNT": "PM"})
                        )
                        cm_by_region = (
                            cm_df.groupby("REGION", as_index=False)["COUNT"]
                            .sum()
                            .rename(columns={"COUNT": "CM"})
                        )
                        breakdown = pm_by_region.merge(cm_by_region, on="REGION", how="outer").fillna(0)
                        breakdown["PM_HRS"] = breakdown["PM"] * pm_assumption
                        breakdown["CM_HRS"] = breakdown["CM"] * cm_assumption
                        breakdown = breakdown.sort_values("REGION")

                        fig2, ax2 = plt.subplots(figsize=(6, max(3, len(breakdown) * 0.4)))
                        y_pos = range(len(breakdown))
                        ax2.barh(
                            breakdown["REGION"], breakdown["PM_HRS"],
                            color=NAVY, edgecolor="none", height=0.6, label="PM",
                        )
                        ax2.barh(
                            breakdown["REGION"], breakdown["CM_HRS"],
                            left=breakdown["PM_HRS"],
                            color=YELLOW, edgecolor="none", height=0.6, label="CM",
                        )
                        ax2.set_title("PM vs CM Hours by Region", fontsize=12, fontweight=600)
                        ax2.set_xlabel("")
                        ax2.spines["top"].set_visible(False)
                        ax2.spines["right"].set_visible(False)
                        ax2.spines["bottom"].set_visible(False)
                        ax2.tick_params(axis="x", labelbottom=False)
                        ax2.tick_params(axis="y", labelsize=9)
                        ax2.legend(loc="lower right", fontsize=9)
                        fig2.tight_layout()
                        st.pyplot(fig2, clear_figure=True)
                    except Exception:
                        st.caption("PM/CM breakdown unavailable.")

                # ── Top projects table ────────────────────────────
                section_header("Top Projects by Backlog")
                top_projects = (
                    backlog_preview.sort_values("HOURS", ascending=False)
                    .head(10)
                    .reset_index(drop=True)
                )
                st.dataframe(top_projects, hide_index=True, use_container_width=True)

        except Exception as exc:
            st.warning(f"Could not load backlog data: {exc}")

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

        # Auto-filter to selected regions from the Scenario Parameters tab
        if selected_regions:
            in_dataset = in_dataset[in_dataset["REGION"].isin(selected_regions)]

        if in_dataset.empty:
            if selected_regions:
                st.info("No projects found for the selected regions. Adjust regions on the Scenario Parameters tab.")
            else:
                st.info("No projects found in the current dataset. Select regions on the Scenario Parameters tab.")
        else:
            # Additional filters to narrow the list further
            filter_cols = st.columns(3)
            with filter_cols[0]:
                region_opts = sorted(in_dataset["REGION"].dropna().unique().tolist())
                filter_region = st.multiselect(
                    "Filter by Region", options=region_opts, placeholder="All selected regions"
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

            already_excluded = {
                p["CCRID"] for p in st.session_state["excluded_projects"]
            }
            available_ccrids = [
                c for c in project_options["CCRID"] if c not in already_excluded
            ]

            st.caption(
                f"{len(available_ccrids)} of {len(project_options)} project(s) available after filters"
            )

            if available_ccrids:
                with st.form("exclude_project_form", clear_on_submit=True):
                    e1, e2 = st.columns([3, 1])
                    with e1:
                        excl_ccrids = st.multiselect(
                            "Projects",
                            options=available_ccrids,
                            format_func=lambda c: ccrid_to_label.get(c, c),
                            placeholder="Select one or more projects",
                        )
                    with e2:
                        excl_date = st.date_input(
                            "Exclude From",
                            value=_saved("start_date", DEFAULT_START_DATE),
                            format="MM/DD/YYYY",
                        )
                    ef1, ef2 = st.columns(2)
                    with ef1:
                        excl_submitted = st.form_submit_button(
                            "Add Exclusion(s)", type="primary"
                        )
                    with ef2:
                        excl_all_submitted = st.form_submit_button(
                            "Exclude All Filtered",
                        )

                if excl_submitted and excl_ccrids:
                    for ccrid in excl_ccrids:
                        st.session_state["excluded_projects"].append(
                            {
                                "CCRID": ccrid,
                                "PROJECT_NAME": ccrid_to_label.get(ccrid, ccrid),
                                "EXCLUDE_FROM": str(excl_date),
                            }
                        )
                    st.toast(
                        f"Excluded {len(excl_ccrids)} project(s)",
                        icon="🚫",
                    )
                    st.rerun()

                if excl_all_submitted:
                    for ccrid in available_ccrids:
                        st.session_state["excluded_projects"].append(
                            {
                                "CCRID": ccrid,
                                "PROJECT_NAME": ccrid_to_label.get(ccrid, ccrid),
                                "EXCLUDE_FROM": str(excl_date),
                            }
                        )
                    st.toast(
                        f"Excluded {len(available_ccrids)} project(s)",
                        icon="🚫",
                    )
                    st.rerun()
            else:
                st.info("All filtered projects are already excluded.")

            # Display current exclusions
            if st.session_state["excluded_projects"]:
                st.divider()
                section_header(
                    "Excluded Projects",
                    f"{len(st.session_state['excluded_projects'])} project(s) excluded",
                )
                st.dataframe(
                    pd.DataFrame(st.session_state["excluded_projects"]),
                    hide_index=True,
                    use_container_width=True,
                )
                if st.button("Clear All Exclusions"):
                    st.session_state["excluded_projects"] = []
                    st.rerun()
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
