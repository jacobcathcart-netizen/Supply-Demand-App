import altair as alt
import pandas as pd
import streamlit as st


def baseline_supply_demand_with_gap(df: pd.DataFrame):
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    chart_df = df.copy()
    chart_df["DATE"] = pd.to_datetime(chart_df["DATE"])

    monthly = (
        chart_df.groupby("DATE", as_index=False)[["BASE_SUPPLY", "DEMAND", "BASE_GAP"]]
        .sum()
        .sort_values("DATE")
    )

    line_df = monthly.melt(
        id_vars="DATE",
        value_vars=["BASE_SUPPLY", "DEMAND", "BASE_GAP"],
        var_name="METRIC",
        value_name="HOURS",
    )

    chart = (
        alt.Chart(line_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("DATE:T", title="Month"),
            y=alt.Y("HOURS:Q", title="Hours"),
            color=alt.Color("METRIC:N", title="Metric"),
            tooltip=["DATE:T", "METRIC:N", "HOURS:Q"],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)


def scenario_supply_demand_with_gap(df: pd.DataFrame):
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    chart_df = df.copy()
    chart_df["DATE"] = pd.to_datetime(chart_df["DATE"])

    monthly = (
        chart_df.groupby("DATE", as_index=False)[["SCENARIO_SUPPLY", "DEMAND", "SCENARIO_GAP"]]
        .sum()
        .sort_values("DATE")
    )

    line_df = monthly.melt(
        id_vars="DATE",
        value_vars=["SCENARIO_SUPPLY", "DEMAND", "SCENARIO_GAP"],
        var_name="METRIC",
        value_name="HOURS",
    )

    chart = (
        alt.Chart(line_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("DATE:T", title="Month"),
            y=alt.Y("HOURS:Q", title="Hours"),
            color=alt.Color("METRIC:N", title="Metric"),
            tooltip=["DATE:T", "METRIC:N", "HOURS:Q"],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)


def supply_delta_chart(df: pd.DataFrame):
    if df.empty:
        st.info("No data available for the selected filters.")
        return

    chart_df = df.copy()
    chart_df["DATE"] = pd.to_datetime(chart_df["DATE"])

    monthly = (
        chart_df.groupby("DATE", as_index=False)[["SUPPLY_DELTA"]]
        .sum()
        .sort_values("DATE")
    )

    chart = (
        alt.Chart(monthly)
        .mark_bar()
        .encode(
            x=alt.X("DATE:T", title="Month"),
            y=alt.Y("SUPPLY_DELTA:Q", title="Supply Delta"),
            tooltip=["DATE:T", "SUPPLY_DELTA:Q"],
        )
        .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)