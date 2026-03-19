import streamlit as st

from logic.scenario import run_scenario
from components.visuals import (
    baseline_supply_demand_with_gap,
    scenario_supply_demand_with_gap,
    supply_delta_chart,
)


st.set_page_config(page_title="Results", layout="wide")
st.title("Scenario Results")

if not st.session_state.get("inputs_saved", False):
    st.warning("Save scenario inputs first.")
    st.stop()

results_df = run_scenario(
    regions=st.session_state["selected_regions"],
    adjustments=st.session_state["adjustments"],
    start_date=st.session_state["scenario"]["start_date"],
    end_date=st.session_state["scenario"]["end_date"],
    adjustment_start_date=st.session_state["adjustment_start_date"],
    pct_decrease=st.session_state["scenario"]["pct_decrease"],
    vac_days_per_month=st.session_state["scenario"]["vac_days_per_month"],
    sick_days_per_month=st.session_state["scenario"]["sick_days_per_month"],
)

st.subheader("Figure 1: Baseline Supply vs Demand vs Gap")
baseline_supply_demand_with_gap(results_df)

st.subheader("Figure 2: Scenario Supply vs Demand vs Gap")
scenario_supply_demand_with_gap(results_df)

st.subheader("Figure 3: Supply Delta")
supply_delta_chart(results_df)

st.subheader("Scenario Output")
st.dataframe(results_df, use_container_width=True)