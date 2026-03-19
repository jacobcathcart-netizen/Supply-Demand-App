import streamlit as st
from datetime import date
from data.snowflake import get_regions_df
from components.adjustments import adjustment_inputs

st.set_page_config(page_title="Inputs", layout="wide", initial_sidebar_state="expanded")
st.title("Scenario Inputs")

# State
st.session_state.setdefault("scenario", {})
st.session_state.setdefault("selected_regions", [])
st.session_state.setdefault("adjustments", {})
st.session_state.setdefault("inputs_saved", False)
st.session_state.setdefault("adjustment_start_date", None)

@st.cache_data(ttl=1800)
def cached_regions():
    # get_regions_df returns a Snowpark DF
    return [r["REGION"] for r in get_regions_df().collect()]

regions_list = cached_regions()

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Scenario settings")

    with st.form("inputs_form"):
        scenario_name = st.text_input("Scenario name", value=st.session_state["scenario"].get("scenario_name", "Scenario 1"))
        st.divider()
        start_date = st.date_input("Start Date", value=date(2025, 1, 1), format="MM/DD/YYYY")
        end_date = st.date_input("End Date", value=date(2025, 12, 31), format="MM/DD/YYYY")

        st.divider()

        pct_decrease = st.number_input("Non-Project Assumption", 0, 100, 15, 1) / 100
        vac_days_per_month = st.number_input("Vacation days per FTE per year", 0, 365, 20, 1) / 12
        sick_days_per_month = st.number_input("Sick days per FTE per year", 0, 365, 8, 1) / 12

        st.divider()

        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"]
        )

        adjustment_start_date = st.date_input(
            "Headcount adjustment start date",
            value=start_date,
            format="MM/DD/YYYY"
        )

        submitted = st.form_submit_button("Save inputs")

    # Validation and save
    if submitted:
        if start_date > end_date:
            st.error("Start Date must be before End Date.")
            st.stop()
        if not selected_regions:
            st.error("Select at least one region.")
            st.stop()

        st.session_state["inputs_saved"] = True
        st.session_state["selected_regions"] = selected_regions
        st.session_state["adjustment_start_date"] = adjustment_start_date

        st.session_state["scenario"] = {
            "scenario_name": scenario_name,
            "pct_decrease": pct_decrease,
            "vac_days_per_month": vac_days_per_month,
            "sick_days_per_month": sick_days_per_month,
            "start_date": start_date,
            "end_date": end_date,
        }

with right:
    st.subheader("Scenario summary")

    if not st.session_state["inputs_saved"]:
        st.info("Save inputs to enable adjustments and results.")
    else:
        s = st.session_state["scenario"]
        st.write(
            {
                "Start Date": s["start_date"],
                "End Date": s["end_date"],
                "Adjustment start": st.session_state["adjustment_start_date"],
                "Regions selected": len(st.session_state["selected_regions"]),
                "Productivity decrease": f"{s['pct_decrease']*100:.0f}%",
                "Vacation days per month": round(s["vac_days_per_month"], 2),
                "Sick days per month": round(s["sick_days_per_month"], 2),
            }
        )

st.divider()

# Adjustments section
if st.session_state["inputs_saved"]:
    adjustments = adjustment_inputs(
        st.session_state["selected_regions"],
        st.session_state["adjustments"]
    )
    st.session_state["adjustments"] = adjustments

    c1, c2 = st.columns([1, 3])
    with c1:
        run = st.button("Run scenario", type="primary")
    with c2:
        st.caption("Runs the scenario and navigates to Results.")

    if run:
        st.switch_page("pages/2_Results.py")