"""Results page — run scenario and display charts / data."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.visuals import (
    baseline_supply_demand_with_gap,
    get_region_backlog,
    scenario_supply_demand_with_gap,
    supply_delta_chart,
)
from data.snowflake import get_backlog
from logic.scenario import run_scenario

st.set_page_config(page_title="Results", layout="wide", initial_sidebar_state="expanded")
st.title("Scenario Results")

# ── Guard: require saved inputs ─────────────────────────────────────

scenario_inputs = st.session_state.get("scenario")
regions: list[str] = st.session_state.get("selected_regions", [])
adjustments: dict[str, int] = st.session_state.get("adjustments", {})
adjustment_start_date = st.session_state.get("adjustment_start_date")

if not scenario_inputs or not regions or adjustment_start_date is None:
    st.warning("Go to **Inputs**, save your settings, and click **Run scenario**.")
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
) -> pd.DataFrame:
    return run_scenario(
        regions=list(regions),
        adjustments=adjustments,
        start_date=start_date,
        end_date=end_date,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        vac_days_per_month=vac_days_per_month,
        sick_days_per_month=sick_days_per_month,
    )


@st.cache_data(show_spinner=False)
def _load_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    df = get_backlog(pm_hours, cm_hours).copy()
    if df.empty:
        return df
    df.columns = ["Region", "COUNT_BACKLOG", "HOUR_BACKLOG"]
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
    ).copy()

if df.empty:
    st.info("No scenario results were returned.")
    st.stop()

df["DATE"] = pd.to_datetime(df["DATE"])

# ── Filters ─────────────────────────────────────────────────────────

st.divider()

f1, f2, f3, f4 = st.columns([1, 2, 1, 1])

with f1:
    region_options = ["All"] + sorted(df["REGION"].dropna().unique().tolist())
    region_filter = st.selectbox("Region", region_options)

with f2:
    project_options = sorted(df["PROJECT_NAME"].dropna().unique().tolist())
    selected_projects = st.multiselect("Project(s)", options=project_options)

with f3:
    month_options = ["All"] + sorted(df["DATE"].dt.date.astype(str).unique().tolist())
    month_filter = st.selectbox("Month", month_options)

with f4:
    show_only_gaps = st.checkbox("Only negative scenario gaps", value=False)

filtered = df.copy()
if region_filter != "All":
    filtered = filtered[filtered["REGION"] == region_filter]
if month_filter != "All":
    filtered = filtered[filtered["DATE"].dt.date.astype(str) == month_filter]
if selected_projects:
    filtered = filtered[filtered["PROJECT_NAME"].isin(selected_projects)]
if show_only_gaps:
    filtered = filtered[filtered["SCENARIO_GAP"] < 0]

# ── Backlog (needed for metrics + charts) ────────────────────────────

backlog_df = _load_backlog(scenario_inputs["pm_assumption"], scenario_inputs["cm_assumption"])

if region_filter == "All":
    backlog = (
        backlog_df.loc[backlog_df["Region"].isin(regions), "HOUR_BACKLOG"].sum()
        if not backlog_df.empty
        else 0.0
    )
else:
    backlog = get_region_backlog(backlog_df, region_filter)

backlog = float(backlog)
baseline_ending_backlog = backlog - filtered["BASE_GAP"].sum()
scenario_ending_backlog = backlog - filtered["SCENARIO_GAP"].sum()
backlog_delta = scenario_ending_backlog - baseline_ending_backlog

# ── KPI metrics ─────────────────────────────────────────────────────

k1, k2, k3 = st.columns(3)
k1.metric("Baseline supply", f"{filtered['BASE_SUPPLY'].sum():,.0f}")
k2.metric("Scenario supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.0f}")
k3.metric("Supply delta", f"{filtered['SUPPLY_DELTA'].sum():,.0f}")

k4, k5, k6, k7 = st.columns(4)
k4.metric("Demand", f"{filtered['DEMAND'].sum():,.0f}")
k5.metric("Baseline gap", f"{filtered['BASE_GAP'].sum():,.0f}")
k6.metric("Scenario gap", f"{filtered['SCENARIO_GAP'].sum():,.0f}")
k7.metric("Net Backlog change", f"{filtered['NET_BACKLOG'].sum():,.0f}")

k8, k9, k10 = st.columns(3)
k8.metric("Baseline ending backlog", f"{baseline_ending_backlog:,.0f}")
k9.metric("Scenario ending backlog", f"{scenario_ending_backlog:,.0f}")
k10.metric(
    "Ending backlog delta",
    f"{backlog_delta:,.0f}",
    delta=f"{backlog_delta:,.0f}",
    delta_color="inverse",
)

# ── Charts ──────────────────────────────────────────────────────────

st.divider()

region_label = "All Selected Regions" if region_filter == "All" else region_filter
st.subheader(f"Monthly supply vs demand — {region_label}")
st.caption("Gap = Supply minus Demand for each month.")

with st.expander("Baseline"):
    fig1 = baseline_supply_demand_with_gap(filtered, region_label=region_label)
    if fig1:
        st.pyplot(fig1, clear_figure=True)

st.divider()

with st.expander("Scenario"):
    fig2 = scenario_supply_demand_with_gap(filtered, region_label=region_label)
    if fig2:
        st.pyplot(fig2, clear_figure=True)

st.divider()

with st.expander("Backlog Summary"):
    fig3 = supply_delta_chart(filtered, region_label=region_label, backlog=backlog)
    if fig3:
        st.pyplot(fig3, clear_figure=True)

# ── Data table & download ──────────────────────────────────────────

st.divider()

display_df = filtered.copy()
display_df["DATE"] = display_df["DATE"].dt.date.astype(str)

st.download_button(
    "Download CSV",
    display_df.to_csv(index=False).encode("utf-8"),
    file_name="scenario_results.csv",
    mime="text/csv",
)

st.caption(f"Showing {len(filtered):,} of {len(df):,} rows")
st.dataframe(display_df, hide_index=True)
