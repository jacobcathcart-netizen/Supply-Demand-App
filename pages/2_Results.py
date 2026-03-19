import streamlit as st
import pandas as pd

from logic.scenario import run_scenario
from components.visuals import (
    baseline_supply_demand_with_gap,
    scenario_supply_demand_with_gap,
    supply_delta_chart,
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


@st.cache_data(show_spinner=False)
def get_results(
    regions,
    adjustments,
    start_date,
    end_date,
    adjustment_start_date,
    pct_decrease,
    vac_days_per_month,
    sick_days_per_month,
):
    return run_scenario(
        regions=regions,
        adjustments=adjustments,
        start_date=start_date,
        end_date=end_date,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        vac_days_per_month=vac_days_per_month,
        sick_days_per_month=sick_days_per_month,
    )


with st.spinner("Running scenario..."):
    df = get_results(
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

st.divider()

f1, f2, f3, f4 = st.columns([1, 2, 1, 1])

with f1:
    region_filter = st.selectbox(
        "Region",
        ["All"] + sorted(df["REGION"].dropna().astype(str).unique().tolist()),
    )

with f2:
    project_search = st.text_input("Search CCRID or project name")

with f3:
    month_choices = ["All"] + sorted(df["DATE"].dt.date.astype(str).unique().tolist())
    month_filter = st.selectbox("Month", month_choices)

with f4:
    show_only_gaps = st.checkbox("Only negative scenario gaps", value=False)

filtered = df.copy()

if region_filter != "All":
    filtered = filtered[filtered["REGION"] == region_filter]

if month_filter != "All":
    filtered = filtered[filtered["DATE"].dt.date.astype(str) == month_filter]

project_search = st.text_input("Search CCRID or project name")

project_options = sorted(df["PROJECT_NAME"].dropna().astype(str).unique().tolist())
selected_projects = st.multiselect("Select projects", options=project_options)

if project_search:
    s = project_search.lower()
    filtered = filtered[
        filtered["PROJECT_NAME"].astype(str).str.lower().str.contains(s, na=False)
        | filtered["CCRID"].astype(str).str.contains(project_search, na=False)
    ]

if selected_projects:
    filtered = filtered[filtered["PROJECT_NAME"].isin(selected_projects)]

if show_only_gaps:
    filtered = filtered[filtered["SCENARIO_GAP"] < 0]

k1, k2, k3 = st.columns(3)
k1.metric("Baseline supply", f"{filtered['BASE_SUPPLY'].sum():,.1f}")
k2.metric("Scenario supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.1f}")
k3.metric("Supply delta", f"{filtered['SUPPLY_DELTA'].sum():,.1f}")

k4, k5, k6 = st.columns(3)
k4.metric("Demand", f"{filtered['DEMAND'].sum():,.1f}")
k5.metric("Baseline gap", f"{filtered['BASE_GAP'].sum():,.1f}")
k6.metric("Scenario gap", f"{filtered['SCENARIO_GAP'].sum():,.1f}")

st.divider()

region_label = "All regions" if region_filter == "All" else region_filter
st.subheader(f"Monthly supply vs demand - {region_label}")
st.caption("Gap labels show Supply minus Demand for each month.")

fig1 = baseline_supply_demand_with_gap(filtered, region_label=region_label)
if fig1 is not None:
    st.pyplot(fig1, clear_figure=True)

fig2 = scenario_supply_demand_with_gap(filtered, region_label=region_label)
if fig2 is not None:
    st.pyplot(fig2, clear_figure=True)

fig3 = supply_delta_chart(filtered, region_label=region_label)
if fig3 is not None:
    st.pyplot(fig3, clear_figure=True)

st.divider()

download_df = filtered.copy()
download_df["DATE"] = download_df["DATE"].dt.date.astype(str)

st.download_button(
    "Download CSV",
    download_df.to_csv(index=False).encode("utf-8"),
    file_name="scenario_results.csv",
    mime="text/csv",
)

st.caption(f"Rows: {len(filtered):,} of {len(df):,}")

display_df = filtered.copy()
display_df["DATE"] = display_df["DATE"].dt.date.astype(str)

st.dataframe(display_df, use_container_width=True, hide_index=True)