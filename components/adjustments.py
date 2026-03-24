import streamlit as st


def adjustment_inputs(regions, saved_adjustments):
    st.subheader("Headcount adjustments")
    st.caption(
        "Adjustments are applied to scenario headcount starting on the adjustment start date."
    )

    top_left, top_right = st.columns([3, 1])
    with top_right:
        if st.button("Reset all", help="Set every region adjustment to 0"):
            for r in regions:
                st.session_state[f"adj_{r}"] = 0

    adjustments = {}

    for region in regions:
        widget_key = f"adj_{region}"

        if widget_key not in st.session_state:
            st.session_state[widget_key] = int(saved_adjustments.get(region, 0))

        adjustments[region] = int(
            st.number_input(
                region,
                step=1,
                key=widget_key,
            )
        )

    return adjustments
