import streamlit as st
from datetime import date

from data.snowflake import get_regions_df
from components.adjustments import adjustment_inputs


st.set_page_config(page_title="Inputs", layout="wide", initial_sidebar_state="expanded")
st.title("Scenario Inputs")

st.session_state.setdefault("scenario", {})
st.session_state.setdefault("selected_regions", [])
st.session_state.setdefault("adjustments", {})
st.session_state.setdefault("inputs_saved", False)
st.session_state.setdefault("adjustment_start_date", None)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_regions():
    regions_df = get_regions_df()
    if regions_df.empty or "REGION" not in regions_df.columns:
        return []
    return regions_df["REGION"].dropna().astype(str).sort_values().tolist()


regions_list = cached_regions()

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Scenario settings")

    with st.form("inputs_form"):
        scenario_name = st.text_input(
            "Scenario name",
            value=st.session_state["scenario"].get("scenario_name", "Scenario 1"),
        )

        st.divider()

        start_date = st.date_input(
            "Start Date",
            value=st.session_state["scenario"].get("start_date", date(2025, 1, 1)),
            format="MM/DD/YYYY",
        )
        end_date = st.date_input(
            "End Date",
            value=st.session_state["scenario"].get("end_date", date(2025, 12, 31)),
            format="MM/DD/YYYY",
        )

        st.divider()

        pct_decrease = (
            st.number_input(
                "Non-Project Assumption",
                min_value=0,
                max_value=100,
                value=int(st.session_state["scenario"].get("pct_decrease", 0.15) * 100),
                step=1,
            )
            / 100
        )

        vac_days_per_month = (
            st.number_input(
                "Vacation days per FTE per year",
                min_value=0,
                max_value=365,
                value=int(
                    round(
                        st.session_state["scenario"].get("vac_days_per_month", 20 / 12)
                        * 12
                    )
                ),
                step=1,
            )
            / 12
        )

        sick_days_per_month = (
            st.number_input(
                "Sick days per FTE per year",
                min_value=0,
                max_value=365,
                value=int(
                    round(
                        st.session_state["scenario"].get("sick_days_per_month", 8 / 12)
                        * 12
                    )
                ),
                step=1,
            )
            / 12
        )
        
        cm_assumption = (
            st.number_input(
                "Hours Per CM Backlog",
                min_value=0
                max_value = 30
                value=int(8)
            ),
            step =1
        )
        

        st.divider()

        selected_regions = st.multiselect(
            "Regions",
            options=regions_list,
            default=st.session_state["selected_regions"],
        )

        adjustment_start_date = st.date_input(
            "Headcount adjustment start date",
            value=st.session_state["adjustment_start_date"] or start_date,
            format="MM/DD/YYYY",
        )
        adjustment_start_date = adjustment_start_date.replace(day=1)
        submitted = st.form_submit_button("Save inputs")

    if submitted:
        if start_date > end_date:
            st.error("Start Date must be before End Date.")
            st.stop()

        if adjustment_start_date < start_date or adjustment_start_date > end_date:
            st.error(
                "Headcount adjustment start date must be within the scenario date range."
            )
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

        st.success("Inputs saved.")

with right:
    st.subheader("Scenario summary")

    if not st.session_state["inputs_saved"]:
        st.info("Save inputs to enable adjustments and results.")
    else:
        s = st.session_state["scenario"]
        st.json(
            {
                "Scenario Name": s["scenario_name"],
                "Start Date": str(s["start_date"]),
                "End Date": str(s["end_date"]),
                "Adjustment Start": str(st.session_state["adjustment_start_date"]),
                "Regions Selected": len(st.session_state["selected_regions"]),
                "Productivity Decrease": f"{s['pct_decrease'] * 100:.0f}%",
                "Vacation Days per Month": round(s["vac_days_per_month"], 2),
                "Sick Days per Month": round(s["sick_days_per_month"], 2),
            }
        )

st.divider()

if st.session_state["inputs_saved"]:
    adjustments = adjustment_inputs(
        st.session_state["selected_regions"],
        st.session_state["adjustments"],
    )
    st.session_state["adjustments"] = adjustments

    c1, c2 = st.columns([1, 3])

    with c1:
        run = st.button("Run scenario", type="primary")

    with c2:
        st.caption("Runs the scenario and navigates to Results.")

    if run:
        st.switch_page("pages/2_Results.py")
