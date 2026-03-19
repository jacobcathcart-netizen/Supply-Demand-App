import streamlit as st
import pandas as pd
from logic.scenario import run_scenario
from components.visuals import (
    baseline_supply_demand_with_gap,
    scenario_supply_demand_with_gap,
)

st.set_page_config(page_title="Results", layout="wide", initial_sidebar_state="expanded")
st.title("Scenario Results")

scenario_inputs = st.session_state.get("scenario")
regions = st.session_state.get("selected_regions", [])
adjustments = st.session_state.get("adjustments", {})
adjustment_start_date = st.session_state.get("adjustment_start_date")

if not scenario_inputs or not regions or adjustment_start_date is None:
    st.warning("Go to Inputs, save inputs, and run the scenario.")
    st.stop()

with st.spinner("Running scenario..."):
    df = run_scenario(
        regions,
        adjustments,
        scenario_inputs["start_date"],
        scenario_inputs["end_date"],
        adjustment_start_date,
        scenario_inputs["pct_decrease"],
        scenario_inputs["vac_days_per_month"],
        scenario_inputs["sick_days_per_month"],
    ).to_pandas()

st.divider()

# Filters
f1, f2, f3, f4 = st.columns([1, 2, 1, 1])

with f1:
    region_filter = st.selectbox("Region", ["All"] + sorted(df["REGION"].unique().tolist()))

with f2:
    project_search = st.text_input("Search CCRID or project name")

with f3:
    month_choices = ["All"] + sorted(pd.to_datetime(df["DATE"]).dt.date.astype(str).unique().tolist())
    month_filter = st.selectbox("Month", month_choices)

with f4:
    show_only_gaps = st.checkbox("Only negative scenario gaps", value=False)

filtered = df.copy()

if region_filter != "All":
    filtered = filtered[filtered["REGION"] == region_filter]

if month_filter != "All":
    filtered = filtered[pd.to_datetime(filtered["DATE"]).dt.date.astype(str) == month_filter]

if project_search:
    s = project_search.lower()
    filtered = filtered[
        filtered["PROJECT_NAME"].str.lower().str.contains(s, na=False)
        | filtered["CCRID"].astype(str).str.contains(project_search)
    ]

if show_only_gaps:
    filtered = filtered[filtered["SCENARIO_GAP"] < 0]

# KPIs (based on filtered)
k1, k2, k3 = st.columns(3)
k1.metric("Baseline supply", f"{filtered['BASE_SUPPLY'].sum():,.1f}")
k2.metric("Scenario supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.1f}")
k3.metric("Supply delta", f"{filtered['SUPPLY_DELTA'].sum():,.1f}")

k4, k5, k6 = st.columns(3)
k4.metric("Demand", f"{filtered['DEMAND'].sum():,.1f}")
k5.metric("Baseline gap", f"{filtered['BASE_GAP'].sum():,.1f}")
k6.metric("Scenario gap", f"{filtered['SCENARIO_GAP'].sum():,.1f}")

st.divider()

# Region label + charts
region_label = "All regions" if region_filter == "All" else region_filter
st.subheader(f"Monthly supply vs demand - {region_label}")
st.caption("Gap labels show Supply minus Demand for each month.")

fig1 = baseline_supply_demand_with_gap(filtered, region_label=region_label)
st.pyplot(fig1, clear_figure=True)

fig2 = scenario_supply_demand_with_gap(filtered, region_label=region_label)
st.pyplot(fig2, clear_figure=True)

st.divider()

# Download
st.download_button(
    "Download CSV",
    filtered.to_csv(index=False).encode("utf-8"),
    file_name="scenario_results.csv",
    mime="text/csv"
)

st.caption(f"Rows: {len(filtered):,} of {len(df):,}")

st.dataframe(filtered, use_container_width=True, hide_index=True)