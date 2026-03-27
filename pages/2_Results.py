"""Results page — run scenario and display charts / data."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.branding import (
    apply_branding,
    section_header,
)
from components.visuals import (
    _monthly_totals,
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    scenario_supply_demand_with_gap,
    sensitivity_fan_chart,
    sensitivity_tornado_chart,
)
from data.snowflake import get_backlog
from logic.scenario import run_scenario
from logic.sensitivity import run_sensitivity

st.set_page_config(
    page_title="Results | CCR",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_branding()

st.title("Scenario Results")

# ── Guard: require saved inputs ─────────────────────────────────────

scenario_inputs = st.session_state.get("scenario")
regions: list[str] = st.session_state.get("selected_regions", [])
adjustments: dict[str, int] = st.session_state.get("adjustments", {})
adjustment_start_date = st.session_state.get("adjustment_start_date")
excluded_ccrids: list[str] = st.session_state.get("excluded_ccrids", [])
custom_projects: list[dict] = st.session_state.get("custom_projects", [])

if not scenario_inputs or not regions or adjustment_start_date is None:
    st.info("No scenario loaded. Go to **Inputs**, save your settings, and click **Run Scenario**.")
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
    excluded_ccrids: tuple[str, ...] = (),
    custom_projects: tuple[tuple, ...] = (),
) -> pd.DataFrame:
    custom_proj_list = [
        {
            "CCRID": c[0],
            "PROJECT_NAME": c[1],
            "REGION": c[2],
            "TOTAL_HOURS": c[3],
            "START_DATE": c[4],
        }
        for c in custom_projects
    ]
    return run_scenario(
        regions=list(regions),
        adjustments=adjustments,
        start_date=start_date,
        end_date=end_date,
        adjustment_start_date=adjustment_start_date,
        pct_decrease=pct_decrease,
        vac_days_per_month=vac_days_per_month,
        sick_days_per_month=sick_days_per_month,
        excluded_ccrids=list(excluded_ccrids),
        custom_projects=custom_proj_list if custom_proj_list else None,
    )


@st.cache_data(show_spinner=False)
def _load_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    df = get_backlog(pm_hours, cm_hours).copy()
    if df.empty:
        return df
    df.columns = ["REGION", "PROJECT_NAME", "CCRID", "COUNT_BACKLOG", "HOUR_BACKLOG"]
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
        excluded_ccrids=tuple(excluded_ccrids),
        custom_projects=tuple(
            (p["CCRID"], p["PROJECT_NAME"], p["REGION"], p["TOTAL_HOURS"], p["START_DATE"])
            for p in custom_projects
        ),
    )

if df.empty:
    st.info("No scenario results were returned.")
    st.stop()

df["DATE"] = pd.to_datetime(df["DATE"])

# ── Filter bar ──────────────────────────────────────────────────────

f1, f2, f3, f4 = st.columns([1, 2, 1, 1])

with f1:
    region_options = ["All"] + sorted(df["REGION"].dropna().unique().tolist())
    region_filter = st.selectbox("Region", region_options)

with f2:
    project_options = sorted(df["PROJECT_NAME"].dropna().unique().tolist())
    selected_projects = st.multiselect(
        "Project(s)", options=project_options, placeholder="All projects"
    )

with f3:
    month_options = ["All Months"] + sorted(
        df["DATE"].dt.strftime("%b %Y").unique().tolist()
    )
    month_filter = st.selectbox("Month", month_options)

with f4:
    show_only_gaps = st.checkbox("Negative gaps only", value=False)

filtered = df
if region_filter != "All":
    filtered = filtered[filtered["REGION"] == region_filter]
if month_filter != "All Months":
    filtered = filtered[filtered["DATE"].dt.strftime("%b %Y") == month_filter]
if selected_projects:
    filtered = filtered[filtered["PROJECT_NAME"].isin(selected_projects)]
if show_only_gaps:
    filtered = filtered[filtered["SCENARIO_GAP"] < 0]

# ── Backlog (needed for metrics + charts) ────────────────────────────

backlog_df = _load_backlog(scenario_inputs["pm_assumption"], scenario_inputs["cm_assumption"])

# Filter backlog to match the region, project, and exclusion selections
filtered_backlog = backlog_df if not backlog_df.empty else pd.DataFrame()
if not filtered_backlog.empty:
    filtered_backlog = filtered_backlog[filtered_backlog["REGION"].isin(regions)]
    if excluded_ccrids:
        filtered_backlog = filtered_backlog[
            ~filtered_backlog["CCRID"].isin(excluded_ccrids)
        ]
    if region_filter != "All":
        filtered_backlog = filtered_backlog[filtered_backlog["REGION"] == region_filter]
    if selected_projects:
        filtered_backlog = filtered_backlog[
            filtered_backlog["PROJECT_NAME"].isin(selected_projects)
        ]

backlog = float(filtered_backlog["HOUR_BACKLOG"].sum()) if not filtered_backlog.empty else 0.0

scenario_ending_backlog = max(backlog - filtered["SCENARIO_GAP"].sum(), 0.0)
backlog_delta = scenario_ending_backlog - backlog

# ── KPI metrics ─────────────────────────────────────────────────────

supply_delta = filtered["SUPPLY_DELTA"].sum()
gap_delta = filtered["SCENARIO_GAP"].sum() - filtered["BASE_GAP"].sum()

# Row 1 — Supply & Demand
section_header("Supply & Demand")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Baseline Supply", f"{filtered['BASE_SUPPLY'].sum():,.0f} hrs")
c2.metric("Scenario Supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs")
c3.metric("Total Demand", f"{filtered['DEMAND'].sum():,.0f} hrs")
c4.metric(
    "Supply Delta",
    f"{supply_delta:,.0f} hrs",
    delta=f"{supply_delta:+,.0f}",
    delta_color="normal",
)

# Row 2 — Gap & Backlog
st.markdown('<div style="height:0.75rem;"></div>', unsafe_allow_html=True)
section_header("Gap & Backlog")
c5, c6, c7, c8 = st.columns(4)
c5.metric("Baseline Gap", f"{filtered['BASE_GAP'].sum():,.0f} hrs")
c6.metric(
    "Scenario Gap",
    f"{filtered['SCENARIO_GAP'].sum():,.0f} hrs",
    delta=f"{gap_delta:+,.0f} vs baseline",
    delta_color="normal",
)
c7.metric("Initial Backlog", f"{backlog:,.0f} hrs")
c8.metric(
    "Ending Backlog",
    f"{scenario_ending_backlog:,.0f} hrs",
    delta=f"{backlog_delta:+,.0f}",
    delta_color="inverse",
)

# ── Charts (tabbed) ──────────────────────────────────────────────────

region_label = "All Selected Regions" if region_filter == "All" else region_filter

# Pre-compute monthly aggregations once — reused by all chart tabs
base_monthly_no_backlog = _monthly_totals(filtered)
base_monthly_with_backlog = _monthly_totals(filtered, backlog=backlog)

tab_baseline, tab_scenario, tab_gap, tab_backlog, tab_sensitivity = st.tabs(
    ["Baseline", "Scenario", "Gap Analysis", "Backlog Trend", "Sensitivity"]
)

with tab_baseline:
    fig1 = baseline_supply_demand_with_gap(filtered, region_label=region_label, monthly=base_monthly_no_backlog)
    if fig1:
        st.caption(
            f"Line chart: baseline supply ({filtered['BASE_SUPPLY'].sum():,.0f} hrs) "
            f"vs demand ({filtered['DEMAND'].sum():,.0f} hrs) over time for {region_label}."
        )
        st.pyplot(fig1, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_scenario:
    fig2 = scenario_supply_demand_with_gap(filtered, region_label=region_label, monthly=base_monthly_no_backlog, adjustment_start_date=adjustment_start_date)
    if fig2:
        st.caption(
            f"Line chart: scenario supply ({filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs) "
            f"vs demand ({filtered['DEMAND'].sum():,.0f} hrs) over time for {region_label}."
        )
        st.pyplot(fig2, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_gap:
    fig3 = gap_bar_chart(filtered, region_label=region_label, backlog=backlog, monthly=base_monthly_with_backlog)
    if fig3:
        base_gap = filtered["BASE_GAP"].sum()
        scen_gap = filtered["SCENARIO_GAP"].sum()
        st.caption(
            f"Bar chart: baseline gap ({base_gap:,.0f} hrs) vs scenario gap "
            f"({scen_gap:,.0f} hrs) by month for {region_label}."
        )
        st.pyplot(fig3, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_backlog:
    fig4 = backlog_trend_chart(filtered, region_label=region_label, backlog=backlog, monthly=base_monthly_with_backlog, adjustment_start_date=adjustment_start_date)
    if fig4:
        st.caption(
            f"Dual-axis chart: cumulative backlog trend and normalized backlog "
            f"(squad-months) over time for {region_label}. "
            f"Ending backlog: {scenario_ending_backlog:,.0f} hrs."
        )
        st.pyplot(fig4, clear_figure=True)
    else:
        st.info("No data to chart for the current filters.")

with tab_sensitivity:
    from config import (
        SENSITIVITY_ADJ_MONTHS,
        SENSITIVITY_CM_HOURS,
        SENSITIVITY_HEADCOUNT,
        SENSITIVITY_PCT_DECREASE,
        SENSITIVITY_PM_HOURS,
        SENSITIVITY_SICK_DAYS,
        SENSITIVITY_VAC_DAYS,
    )

    # ── Interactive sensitivity controls (outside form → instant reruns) ──
    _SENS_PARAMS = [
        ("Headcount adj.", "sens_hc", SENSITIVITY_HEADCOUNT, -50, 50, True),
        ("Adj. month", "sens_adj_mo", SENSITIVITY_ADJ_MONTHS, 1, 12, False),
        ("Non-project %", "sens_pct", SENSITIVITY_PCT_DECREASE, 1, 50, False),
        ("Vacation days", "sens_vac", SENSITIVITY_VAC_DAYS, 1, 30, False),
        ("Sick days", "sens_sick", SENSITIVITY_SICK_DAYS, 1, 30, False),
        ("CM hours", "sens_cm", SENSITIVITY_CM_HOURS, 1, 15, False),
        ("PM hours", "sens_pm", SENSITIVITY_PM_HOURS, 1, 15, False),
    ]

    sc1, sc2, sc3 = st.columns(3)
    sens_values: dict[str, int] = {}
    for idx, (label, key, default, lo, hi, default_on) in enumerate(_SENS_PARAMS):
        col = [sc1, sc2, sc3][idx % 3]
        with col:
            on = st.checkbox(label, value=default_on, key=f"{key}_on")
            if on:
                sens_values[key] = st.number_input(
                    f"{label} (±)",
                    min_value=lo,
                    max_value=hi,
                    value=default,
                    step=1,
                    key=f"{key}_val",
                )

    # ── Build sensitivity config from interactive controls ──
    sens_config = {
        "enabled": True,
        "headcount_delta": sens_values.get("sens_hc", 0),
        "adj_months_delta": sens_values.get("sens_adj_mo", 0),
        "pct_decrease_delta": sens_values.get("sens_pct", 0) / 100 if "sens_pct" in sens_values else 0,
        "vac_days_delta": sens_values.get("sens_vac", 0) / 12 if "sens_vac" in sens_values else 0,
        "sick_days_delta": sens_values.get("sens_sick", 0) / 12 if "sens_sick" in sens_values else 0,
        "cm_assumption_delta": sens_values.get("sens_cm", 0),
        "pm_assumption_delta": sens_values.get("sens_pm", 0),
    }

    any_active = any(v != 0 for v in [
        sens_config["headcount_delta"],
        sens_config["adj_months_delta"],
        sens_config["pct_decrease_delta"],
        sens_config["vac_days_delta"],
        sens_config["sick_days_delta"],
        sens_config["cm_assumption_delta"],
        sens_config["pm_assumption_delta"],
    ])

    if not any_active:
        st.info("Toggle at least one sensitivity parameter above to see the analysis.")
    else:
        with st.spinner("Running sensitivity analysis..."):
            _base_kwargs = {
                "regions": tuple(regions),
                "adjustments": adjustments,
                "start_date": scenario_inputs["start_date"],
                "end_date": scenario_inputs["end_date"],
                "adjustment_start_date": adjustment_start_date,
                "pct_decrease": scenario_inputs["pct_decrease"],
                "vac_days_per_month": scenario_inputs["vac_days_per_month"],
                "sick_days_per_month": scenario_inputs["sick_days_per_month"],
                "excluded_ccrids": tuple(excluded_ccrids),
                "custom_projects": tuple(
                    (p["CCRID"], p["PROJECT_NAME"], p["REGION"], p["TOTAL_HOURS"], p["START_DATE"])
                    for p in custom_projects
                ),
                "pm_assumption": scenario_inputs["pm_assumption"],
                "cm_assumption": scenario_inputs["cm_assumption"],
            }

            def _sens_run(**kwargs: object) -> pd.DataFrame:
                kw = {k: v for k, v in kwargs.items() if k not in ("pm_assumption", "cm_assumption")}
                result = _run(**kw)
                result["DATE"] = pd.to_datetime(result["DATE"])
                return result

            def _sens_backlog(pm_hours: int, cm_hours: int) -> float:
                bl = _load_backlog(pm_hours, cm_hours)
                if bl.empty:
                    return 0.0
                fb = bl[bl["REGION"].isin(regions)]
                if excluded_ccrids:
                    fb = fb[~fb["CCRID"].isin(excluded_ccrids)]
                if region_filter != "All":
                    fb = fb[fb["REGION"] == region_filter]
                if selected_projects:
                    fb = fb[fb["PROJECT_NAME"].isin(selected_projects)]
                return float(fb["HOUR_BACKLOG"].sum()) if not fb.empty else 0.0

            sens_result = run_sensitivity(
                base_kwargs=_base_kwargs,
                sensitivity_config=sens_config,
                base_backlog=backlog,
                base_df=filtered,
                run_fn=_sens_run,
                backlog_fn=_sens_backlog,
            )

        if not sens_result.param_results:
            st.info("No sensitivity results. Adjust the ranges above.")
        else:
            # Fan chart
            fig_fan = sensitivity_fan_chart(
                base_monthly=sens_result.base_monthly,
                envelope_min=sens_result.envelope_min,
                envelope_max=sens_result.envelope_max,
                param_results=sens_result.param_results,
                region_label=region_label,
                adjustment_start_date=adjustment_start_date,
            )
            if fig_fan:
                st.caption(
                    f"Shaded area shows the range of possible backlog outcomes "
                    f"when each input is varied independently. "
                    f"Base ending backlog: {sens_result.base_ending_backlog:,.0f} hrs."
                )
                st.pyplot(fig_fan, clear_figure=True)

            st.divider()

            # Tornado chart
            fig_tornado = sensitivity_tornado_chart(
                param_results=sens_result.param_results,
                base_ending_backlog=sens_result.base_ending_backlog,
            )
            if fig_tornado:
                st.caption(
                    "Bars show the impact of each input on ending backlog. "
                    "Wider bars indicate higher sensitivity."
                )
                st.pyplot(fig_tornado, clear_figure=True)

            st.divider()

            # Summary table
            section_header("Sensitivity Summary")
            summary_rows = []
            for pr in sorted(
                sens_result.param_results,
                key=lambda p: abs(p.high_ending_backlog - p.low_ending_backlog),
                reverse=True,
            ):
                summary_rows.append(
                    {
                        "Parameter": pr.name,
                        "Low Value": f"{pr.low_value:,.2f}" if isinstance(pr.low_value, float) else str(pr.low_value),
                        "Base Value": f"{pr.base_value:,.2f}" if isinstance(pr.base_value, float) else str(pr.base_value),
                        "High Value": f"{pr.high_value:,.2f}" if isinstance(pr.high_value, float) else str(pr.high_value),
                        "Low Backlog": f"{pr.low_ending_backlog:,.0f} hrs",
                        "High Backlog": f"{pr.high_ending_backlog:,.0f} hrs",
                        "Range": f"{abs(pr.high_ending_backlog - pr.low_ending_backlog):,.0f} hrs",
                    }
                )
            st.dataframe(
                pd.DataFrame(summary_rows),
                hide_index=True,
                use_container_width=True,
            )

# ── Data table & download ──────────────────────────────────────────

with st.expander(f"Detail Data ({len(filtered):,} of {len(df):,} rows)", expanded=False):
    display_df = filtered.assign(DATE=filtered["DATE"].dt.strftime("%b %Y"))

    st.download_button(
        "Download CSV",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name="scenario_results.csv",
        mime="text/csv",
    )

    st.dataframe(display_df, hide_index=True, width="stretch")
