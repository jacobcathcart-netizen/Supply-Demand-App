"""Results page — run scenario and display charts / data."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.branding import (
    GRAY_600,
    NAVY,
    apply_branding,
    section_header,
)
from components.visuals import (
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    scenario_supply_demand_with_gap,
)
from data.snowflake import get_backlog
from logic.scenario import run_scenario

st.set_page_config(
    page_title="Results | CCR",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_branding()

st.title("Scenario Results")

# ── Guard: require saved inputs ─────────────────────────────────────

scenario_inputs = st.session_state.get("scenario")
regions: list[str] = st.session_state.get("selected_regions", [])
adjustments: dict[str, int] = st.session_state.get("adjustments", {})
adjustment_start_date = st.session_state.get("adjustment_start_date")
excluded_ccrids: list[str] = st.session_state.get("excluded_ccrids", [])
custom_projects: list[dict] = st.session_state.get("custom_projects", [])

if not scenario_inputs or not regions or adjustment_start_date is None:
    st.info("No scenario loaded. Go to **Inputs**, save your settings, and click **Run Scenario**.")
    st.stop()


# ── Cached computation ──────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _run(
    regions: tuple[str, ...],
    adjustments: dict[str, int],
    start_date,
    end_date,
    adjustment_start_date,
    pct_decrease: float,
    vac_days_per_month: float,
    sick_days_per_month: float,
    excluded_ccrids: tuple[str, ...] = (),
    custom_projects: tuple[tuple, ...] = (),
) -> pd.DataFrame:
    custom_proj_list = [
        {
            "CCRID": c[0],
            "PROJECT_NAME": c[1],
            "REGION": c[2],
            "TOTAL_HOURS": c[3],
            "START_DATE": c[4],
        }
        for c in custom_projects
    ]
    return run_scenario(
        regions=list(regions),
        adjustments=adjustments,
        start_date=start_date,
        end_date=end_date,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        vac_days_per_month=vac_days_per_month,
        sick_days_per_month=sick_days_per_month,
        excluded_ccrids=list(excluded_ccrids),
        custom_projects=custom_proj_list if custom_proj_list else None,
    )


@st.cache_data(show_spinner=False)
def _load_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    df = get_backlog(pm_hours, cm_hours).copy()
    if df.empty:
        return df
    df.columns = ["REGION", "PROJECT_NAME", "CCRID", "COUNT_BACKLOG", "HOUR_BACKLOG"]
    return df


# ── Run scenario ───────────────────────────────────────────────────

with st.spinner("Running scenario..."):
    df = _run(
        tuple(regions),
        adjustments,
        scenario_inputs["start_date"],
        scenario_inputs["end_date"],
        adjustment_start_date,
        scenario_inputs["pct_decrease"],
        scenario_inputs["vac_days_per_month"],
        scenario_inputs["sick_days_per_month"],
        excluded_ccrids=tuple(excluded_ccrids),
        custom_projects=tuple(
            (p["CCRID"], p["PROJECT_NAME"], p["REGION"], p["TOTAL_HOURS"], p["START_DATE"])
            for p in custom_projects
        ),
    ).copy()

if df.empty:
    st.info("No scenario results were returned.")
    st.stop()

df["DATE"] = pd.to_datetime(df["DATE"])

# ── Filter bar ──────────────────────────────────────────────────────

f1, f2, f3, f4 = st.columns([1, 2, 1, 1])

with f1:
    region_options = ["All"] + sorted(df["REGION"].dropna().unique().tolist())
    region_filter = st.selectbox("Region", region_options)

with f2:
    project_options = sorted(df["PROJECT_NAME"].dropna().unique().tolist())
    selected_projects = st.multiselect(
        "Project(s)", options=project_options, placeholder="All projects"
    )

with f3:
    month_options = ["All Months"] + sorted(
        df["DATE"].dt.strftime("%b %Y").unique().tolist()
    )
    month_filter = st.selectbox("Month", month_options)

with f4:
    show_only_gaps = st.checkbox("Negative gaps only", value=False)

filtered = df.copy()
if region_filter != "All":
    filtered = filtered[filtered["REGION"] == region_filter]
if month_filter != "All Months":
    filtered = filtered[filtered["DATE"].dt.strftime("%b %Y") == month_filter]
if selected_projects:
    filtered = filtered[filtered["PROJECT_NAME"].isin(selected_projects)]
if show_only_gaps:
    filtered = filtered[filtered["SCENARIO_GAP"] < 0]

# ── Backlog (needed for metrics + charts) ────────────────────────────

backlog_df = _load_backlog(scenario_inputs["pm_assumption"], scenario_inputs["cm_assumption"])

# Filter backlog to match the region, project, and exclusion selections
filtered_backlog = backlog_df.copy() if not backlog_df.empty else pd.DataFrame()
if not filtered_backlog.empty:
    filtered_backlog = filtered_backlog[filtered_backlog["REGION"].isin(regions)]
    if excluded_ccrids:
        filtered_backlog = filtered_backlog[
            ~filtered_backlog["CCRID"].isin(excluded_ccrids)
        ]
    if region_filter != "All":
        filtered_backlog = filtered_backlog[filtered_backlog["REGION"] == region_filter]
    if selected_projects:
        filtered_backlog = filtered_backlog[
            filtered_backlog["PROJECT_NAME"].isin(selected_projects)
        ]

backlog = float(filtered_backlog["HOUR_BACKLOG"].sum()) if not filtered_backlog.empty else 0.0

scenario_ending_backlog = max(backlog - filtered["SCENARIO_GAP"].sum(), 0.0)
backlog_delta = backlog - scenario_ending_backlog

# ── KPI metrics ─────────────────────────────────────────────────────

supply_delta = filtered["SUPPLY_DELTA"].sum()
gap_delta = filtered["SCENARIO_GAP"].sum() - filtered["BASE_GAP"].sum()

# Row 1 — Supply & Demand
c1, c2, c3, c4 = st.columns(4)
c1.metric("Baseline Supply", f"{filtered['BASE_SUPPLY'].sum():,.0f} hrs")
c2.metric("Scenario Supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs")
c3.metric("Total Demand", f"{filtered['DEMAND'].sum():,.0f} hrs")
c4.metric(
    "Supply Delta",
    f"{supply_delta:,.0f} hrs",
    delta=f"{supply_delta:+,.0f}",
    delta_color="normal",
)

# Row 2 — Gap & Backlog
c5, c6, c7, c8 = st.columns(4)
c5.metric("Baseline Gap", f"{filtered['BASE_GAP'].sum():,.0f} hrs")
c6.metric(
    "Scenario Gap",
    f"{filtered['SCENARIO_GAP'].sum():,.0f} hrs",
    delta=f"{gap_delta:+,.0f} vs baseline",
    delta_color="normal",
)
c7.metric("Ending Backlog", f"{scenario_ending_backlog:,.0f} hrs")
c8.metric(
    "Backlog Change",
    f"{backlog_delta:,.0f} hrs",
    delta=f"{backlog_delta:+,.0f}",
    delta_color="inverse",
)

# ── Charts (tabbed) ──────────────────────────────────────────────────

region_label = "All Selected Regions" if region_filter == "All" else region_filter

tab_baseline, tab_scenario, tab_gap, tab_backlog = st.tabs(
    ["Baseline", "Scenario", "Gap Analysis", "Backlog Trend"]
)

with tab_baseline:
    fig1 = baseline_supply_demand_with_gap(filtered, region_label=region_label)
    if fig1:
        st.caption(
            f"Line chart: baseline supply ({filtered['BASE_SUPPLY'].sum():,.0f} hrs) "
            f"vs demand ({filtered['DEMAND'].sum():,.0f} hrs) over time for {region_label}."
        )
        st.pyplot(fig1, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_scenario:
    fig2 = scenario_supply_demand_with_gap(filtered, region_label=region_label)
    if fig2:
        st.caption(
            f"Line chart: scenario supply ({filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs) "
            f"vs demand ({filtered['DEMAND'].sum():,.0f} hrs) over time for {region_label}."
        )
        st.pyplot(fig2, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_gap:
    fig3 = gap_bar_chart(filtered, region_label=region_label, backlog=backlog)
    if fig3:
        base_gap = filtered["BASE_GAP"].sum()
        scen_gap = filtered["SCENARIO_GAP"].sum()
        st.caption(
            f"Bar chart: baseline gap ({base_gap:,.0f} hrs) vs scenario gap "
            f"({scen_gap:,.0f} hrs) by month for {region_label}."
        )
        st.pyplot(fig3, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_backlog:
    fig4 = backlog_trend_chart(filtered, region_label=region_label, backlog=backlog)
    if fig4:
        st.caption(
            f"Dual-axis chart: cumulative backlog trend and normalized backlog "
            f"(squad-months) over time for {region_label}. "
            f"Ending backlog: {scenario_ending_backlog:,.0f} hrs."
        )
        st.pyplot(fig4, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

# ── Data table & download ──────────────────────────────────────────

with st.expander(f"Detail Data ({len(filtered):,} of {len(df):,} rows)", expanded=False):
    display_df = filtered.copy()
    display_df["DATE"] = display_df["DATE"].dt.strftime("%b %Y")

    st.download_button(
        "Download CSV",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name="scenario_results.csv",
        mime="text/csv",
    )

    st.dataframe(display_df, hide_index=True, width="stretch")
