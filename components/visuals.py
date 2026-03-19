import streamlit as st


def adjustment_inputs(regions, saved_adjustments):
    st.subheader("Headcount adjustments")
    st.caption("Adjustments are applied to scenario headcount starting on the adjustment start date.")

    _, top_right = st.columns([3, 1])

    with top_right:
        if st.button("Reset all", help="Set every region adjustment to 0"):
            for region in regions:
                st.session_state[f"adj_{region}"] = 0

    adjustments = {}

    for region in regions:
        widget_key = f"adj_{region}"

        if widget_key not in st.session_state:
            st.session_state[widget_key] = int(saved_adjustments.get(region, 0))

        adjustments[region] = int(
            st.number_input(
                label=region,
                min_value=-1000,
                max_value=1000,
                step=1,
                key=widget_key,
            )
        )

    return adjustments