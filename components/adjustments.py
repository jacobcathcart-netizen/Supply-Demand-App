"""Headcount-adjustment input widget for the Inputs page."""

from __future__ import annotations

import streamlit as st

def adjustment_inputs(
    regions: list[str],
    saved_adjustments: dict[str, int],
) -> dict[str, int]:
    """Render a number input per region and return the adjustment map.

    Parameters
    ----------
    regions:
        Ordered list of region names to show.
    saved_adjustments:
        Previously saved values (used to seed widget defaults on first
        render).

    Returns
    -------
    dict[str, int]
        Region → headcount adjustment.
    """
    # Reset button
    _, btn_col = st.columns([3, 1])
    with btn_col:
        if st.button("↺ Reset All", help="Set every region adjustment to 0"):
            for r in regions:
                st.session_state[f"adj_{r}"] = 0

    # Grid layout: 3 columns for regions
    adjustments: dict[str, int] = {}
    cols_per_row = 3
    for i in range(0, len(regions), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(regions):
                break
            region = regions[idx]
            key = f"adj_{region}"
            if key not in st.session_state:
                st.session_state[key] = int(saved_adjustments.get(region, 0))
            with col:
                adjustments[region] = int(
                    st.number_input(region, step=1, key=key)
                )

    return adjustments
