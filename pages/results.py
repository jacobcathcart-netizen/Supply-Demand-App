"""Results page — run scenario and display charts / data."""

from __future__ import annotations

from datetime import date

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import callback, dcc, html, Input, Output, State, no_update

from components.branding import section_header
from components.charts import (
    _monthly_totals,
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    scenario_supply_demand_with_gap,
    sensitivity_fan_chart,
    sensitivity_tornado_chart,
)
from components.kpi_cards import kpi_row
from config import (
    DEFAULT_CM_HOURS,
    DEFAULT_PM_HOURS,
    SENSITIVITY_ADJ_MONTHS,
    SENSITIVITY_CM_HOURS,
    SENSITIVITY_HEADCOUNT,
    SENSITIVITY_PCT_DECREASE,
    SENSITIVITY_PM_HOURS,
    SENSITIVITY_SICK_DAYS,
    SENSITIVITY_VAC_DAYS,
)

dash.register_page(__name__, path="/results", name="Results", order=2)


# ── Helpers ──────────────────────────────────────────────────────────


def _run_scenario_from_store(store_data: dict) -> pd.DataFrame:
    """Execute run_scenario using params from the session store."""
    from logic.scenario import run_scenario

    s = store_data["scenario"]
    regions = store_data["selected_regions"]
    adjustments = store_data.get("adjustments", {})

    excl_list = None
    if store_data.get("excluded_projects"):
        excl_list = [
            {"CCRID": p["CCRID"], "EXCLUDE_FROM": p["EXCLUDE_FROM"]}
            for p in store_data["excluded_projects"]
        ]

    custom_list = None
    if store_data.get("custom_projects"):
        custom_list = store_data["custom_projects"]

    return run_scenario(
        regions=regions,
        adjustments=adjustments,
        start_date=date.fromisoformat(s["start_date"]) if isinstance(s["start_date"], str) else s["start_date"],
        end_date=date.fromisoformat(s["end_date"]) if isinstance(s["end_date"], str) else s["end_date"],
        adjustment_start_date=(
            date.fromisoformat(store_data["adjustment_start_date"])
            if isinstance(store_data["adjustment_start_date"], str)
            else store_data["adjustment_start_date"]
        ),
        pct_decrease=s["pct_decrease"],
        vac_days_per_month=s["vac_days_per_month"],
        sick_days_per_month=s["sick_days_per_month"],
        swat_allocation=s.get("swat_allocation", 0),
        excluded_projects=excl_list,
        custom_projects=custom_list,
    )


def _load_backlog(pm_hours: int, cm_hours: int) -> pd.DataFrame:
    from data.snowflake import get_backlog
    df = get_backlog(pm_hours, cm_hours).copy()
    if df.empty:
        return df
    df.columns = ["REGION", "PROJECT_NAME", "CCRID", "COUNT_BACKLOG", "HOUR_BACKLOG"]
    return df


# ── Layout ────────────────────────────────────────────────────────────

layout = dbc.Container(
    [
        html.H1("Scenario Results"),
        # No-data guard
        html.Div(id="results-guard"),
        # Filter bar
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Region", size="sm"),
                        dcc.Dropdown(id="filter-region", placeholder="All"),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label("Project(s)", size="sm"),
                        dcc.Dropdown(id="filter-projects", multi=True, placeholder="All projects"),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        dbc.Label("Month", size="sm"),
                        dcc.Dropdown(id="filter-month", placeholder="All Months"),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label(" ", size="sm", className="d-block"),
                        dbc.Checklist(
                            id="filter-neg-gaps",
                            options=[{"label": "Negative gaps only", "value": "neg"}],
                            value=[],
                            switch=True,
                        ),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        dbc.Label(" ", size="sm", className="d-block"),
                        dbc.Button(
                            "Refresh",
                            id="btn-refresh-results",
                            outline=True,
                            color="info",
                            size="sm",
                            className="w-100",
                        ),
                    ],
                    md=2,
                ),
            ],
            className="mb-4",
        ),
        # KPIs
        html.Div(id="kpi-supply-demand"),
        html.Div(id="kpi-gap-backlog", className="mt-2"),
        # Chart tabs
        dbc.Tabs(
            [
                dbc.Tab(label="Baseline", tab_id="tab-baseline"),
                dbc.Tab(label="Scenario", tab_id="tab-scenario"),
                dbc.Tab(label="Gap Analysis", tab_id="tab-gap"),
                dbc.Tab(label="Backlog Trend", tab_id="tab-backlog"),
                dbc.Tab(label="Sensitivity", tab_id="tab-sensitivity"),
            ],
            id="chart-tabs",
            active_tab="tab-baseline",
            className="mt-4",
        ),
        html.Div(id="chart-content", className="mt-3"),
        # Export section
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(
                    [
                        section_header("Export"),
                        dbc.Button(
                            "Download PowerPoint",
                            id="btn-download-pptx",
                            outline=True,
                            color="info",
                            className="me-2",
                        ),
                        dcc.Download(id="download-pptx"),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        section_header("Data"),
                        dbc.Button(
                            "Download CSV",
                            id="btn-download-csv",
                            outline=True,
                            color="info",
                            className="me-2",
                        ),
                        dcc.Download(id="download-csv"),
                    ],
                    md=6,
                ),
            ],
        ),
        # Detail data
        dbc.Accordion(
            [
                dbc.AccordionItem(
                    html.Div(id="detail-data-table"),
                    title="Detail Data",
                ),
            ],
            start_collapsed=True,
            className="mt-4",
        ),
        # Hidden stores for computed data
        dcc.Store(id="scenario-df-store"),
    ],
    fluid=True,
    className="py-4",
)


# ── Main computation callback ────────────────────────────────────────


@callback(
    Output("results-guard", "children"),
    Output("scenario-df-store", "data"),
    Output("filter-region", "options"),
    Output("filter-projects", "options"),
    Output("filter-month", "options"),
    Input("scenario-store", "data"),
    Input("btn-refresh-results", "n_clicks"),
)
def run_scenario_cb(store_data, _):
    if not store_data or not store_data.get("inputs_saved"):
        return (
            dbc.Alert(
                "No scenario loaded. Go to Inputs, save your settings, and click Run Scenario.",
                color="info",
            ),
            None,
            [],
            [],
            [],
        )

    try:
        df = _run_scenario_from_store(store_data)
    except Exception as exc:
        return dbc.Alert(f"Scenario failed: {exc}", color="danger"), None, [], [], []

    if df.empty:
        return dbc.Alert("No scenario results were returned.", color="info"), None, [], [], []

    df["DATE"] = pd.to_datetime(df["DATE"])

    # Prepare filter options
    region_opts = [{"label": "All", "value": "All"}] + [
        {"label": r, "value": r} for r in sorted(df["REGION"].dropna().unique())
    ]
    project_opts = [
        {"label": p, "value": p} for p in sorted(df["PROJECT_NAME"].dropna().unique())
    ]
    month_opts = [{"label": "All Months", "value": "All Months"}] + [
        {"label": m, "value": m} for m in sorted(df["DATE"].dt.strftime("%b %Y").unique())
    ]

    # Store df as JSON for other callbacks
    df_json = df.to_json(date_format="iso", orient="split")

    return html.Div(), df_json, region_opts, project_opts, month_opts


# ── KPI + Chart callback ────────────────────────────────────────────


@callback(
    Output("kpi-supply-demand", "children"),
    Output("kpi-gap-backlog", "children"),
    Output("chart-content", "children"),
    Output("detail-data-table", "children"),
    Input("scenario-df-store", "data"),
    Input("filter-region", "value"),
    Input("filter-projects", "value"),
    Input("filter-month", "value"),
    Input("filter-neg-gaps", "value"),
    Input("chart-tabs", "active_tab"),
    State("scenario-store", "data"),
)
def update_dashboard(df_json, region_filter, selected_projects, month_filter, neg_gaps, active_tab, store_data):
    if not df_json or not store_data:
        return html.Div(), html.Div(), html.Div(), html.Div()

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])

    scenario_inputs = store_data["scenario"]
    regions = store_data["selected_regions"]
    excluded_projects = store_data.get("excluded_projects", [])
    adjustment_start_date = store_data.get("adjustment_start_date")

    # Apply filters
    filtered = df.copy()
    if region_filter and region_filter != "All":
        filtered = filtered[filtered["REGION"] == region_filter]
    if month_filter and month_filter != "All Months":
        filtered = filtered[filtered["DATE"].dt.strftime("%b %Y") == month_filter]
    if selected_projects:
        filtered = filtered[filtered["PROJECT_NAME"].isin(selected_projects)]
    if "neg" in (neg_gaps or []):
        filtered = filtered[filtered["SCENARIO_GAP"] < 0]

    if filtered.empty:
        return (
            html.Div(),
            html.Div(),
            dbc.Alert("No data matches the current filters.", color="info"),
            html.Div(),
        )

    # Backlog
    backlog_df = _load_backlog(scenario_inputs["pm_assumption"], scenario_inputs["cm_assumption"])
    filtered_backlog = backlog_df if not backlog_df.empty else pd.DataFrame()
    if not filtered_backlog.empty:
        filtered_backlog = filtered_backlog[filtered_backlog["REGION"].isin(regions)]
        if excluded_projects:
            excl_ccrids = {p["CCRID"] for p in excluded_projects}
            filtered_backlog = filtered_backlog[~filtered_backlog["CCRID"].isin(excl_ccrids)]
        if region_filter and region_filter != "All":
            filtered_backlog = filtered_backlog[filtered_backlog["REGION"] == region_filter]
        if selected_projects:
            filtered_backlog = filtered_backlog[filtered_backlog["PROJECT_NAME"].isin(selected_projects)]

    backlog = float(filtered_backlog["HOUR_BACKLOG"].sum()) if not filtered_backlog.empty else 0.0
    scenario_ending_backlog = max(backlog - filtered["SCENARIO_GAP"].sum(), 0.0)
    backlog_delta = scenario_ending_backlog - backlog

    supply_delta = filtered["SUPPLY_DELTA"].sum()
    gap_delta = filtered["SCENARIO_GAP"].sum() - filtered["BASE_GAP"].sum()

    # KPIs
    kpi1 = kpi_row([
        {"label": "Baseline Supply", "value": f"{filtered['BASE_SUPPLY'].sum():,.0f} hrs"},
        {"label": "Scenario Supply", "value": f"{filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs"},
        {"label": "Total Demand", "value": f"{filtered['DEMAND'].sum():,.0f} hrs"},
        {"label": "Supply Delta", "value": f"{supply_delta:,.0f} hrs", "delta": f"{supply_delta:+,.0f}"},
    ])
    kpi2 = kpi_row([
        {"label": "Baseline Gap", "value": f"{filtered['BASE_GAP'].sum():,.0f} hrs"},
        {"label": "Scenario Gap", "value": f"{filtered['SCENARIO_GAP'].sum():,.0f} hrs", "delta": f"{gap_delta:+,.0f} vs baseline"},
        {"label": "Initial Backlog", "value": f"{backlog:,.0f} hrs"},
        {"label": "Ending Backlog", "value": f"{scenario_ending_backlog:,.0f} hrs", "delta": f"{backlog_delta:+,.0f}"},
    ])

    # Pre-compute monthly
    region_label = scenario_inputs.get("scenario_name", "Scenario")
    base_monthly_no_backlog = _monthly_totals(filtered)
    base_monthly_with_backlog = _monthly_totals(filtered, backlog=backlog)

    # Chart content
    chart = html.Div()

    if active_tab == "tab-baseline":
        fig = baseline_supply_demand_with_gap(filtered, region_label=region_label, monthly=base_monthly_no_backlog)
        if fig:
            chart = dcc.Graph(figure=fig, config={"displayModeBar": True, "toImageButtonOptions": {"format": "png", "scale": 2}})
        else:
            chart = dbc.Alert("No data to chart.", color="info")

    elif active_tab == "tab-scenario":
        fig = scenario_supply_demand_with_gap(
            filtered, region_label=region_label, monthly=base_monthly_no_backlog,
            adjustment_start_date=adjustment_start_date,
        )
        if fig:
            chart = dcc.Graph(figure=fig, config={"displayModeBar": True})
        else:
            chart = dbc.Alert("No data to chart.", color="info")

    elif active_tab == "tab-gap":
        fig = gap_bar_chart(filtered, region_label=region_label, backlog=backlog, monthly=base_monthly_with_backlog)
        if fig:
            chart = dcc.Graph(figure=fig, config={"displayModeBar": True})
        else:
            chart = dbc.Alert("No data to chart.", color="info")

    elif active_tab == "tab-backlog":
        fig = backlog_trend_chart(
            filtered, region_label=region_label, backlog=backlog,
            monthly=base_monthly_with_backlog, adjustment_start_date=adjustment_start_date,
        )
        if fig:
            chart = dcc.Graph(figure=fig, config={"displayModeBar": True})
        else:
            chart = dbc.Alert("No data to chart.", color="info")

    elif active_tab == "tab-sensitivity":
        chart = _build_sensitivity_tab(
            filtered, store_data, backlog, region_label,
            adjustment_start_date, region_filter, selected_projects,
        )

    # Detail table
    display_df = filtered.assign(DATE=filtered["DATE"].dt.strftime("%b %Y"))
    detail = dag.AgGrid(
        rowData=display_df.to_dict("records"),
        columnDefs=[{"field": c, "headerName": c} for c in display_df.columns],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        dashGridOptions={"pagination": True, "paginationPageSize": 25},
        style={"height": "400px"},
        className="ag-theme-alpine",
    )

    return kpi1, kpi2, chart, detail


def _build_sensitivity_tab(
    filtered, store_data, backlog, region_label, adjustment_start_date,
    region_filter, selected_projects,
):
    """Build the sensitivity analysis tab content."""
    from logic.sensitivity import run_sensitivity

    regions = store_data["selected_regions"]
    scenario_inputs = store_data["scenario"]
    excluded_projects = store_data.get("excluded_projects", [])
    custom_projects = store_data.get("custom_projects", [])

    # Sensitivity controls
    _SENS_PARAMS = [
        ("Headcount adj.", "sens_hc", SENSITIVITY_HEADCOUNT),
        ("Adj. month", "sens_adj_mo", SENSITIVITY_ADJ_MONTHS),
        ("Non-project %", "sens_pct", SENSITIVITY_PCT_DECREASE),
        ("Vacation days", "sens_vac", SENSITIVITY_VAC_DAYS),
        ("Sick days", "sens_sick", SENSITIVITY_SICK_DAYS),
        ("CM hours", "sens_cm", SENSITIVITY_CM_HOURS),
        ("PM hours", "sens_pm", SENSITIVITY_PM_HOURS),
    ]

    # Build simple config with defaults (headcount on by default)
    sens_config = {
        "enabled": True,
        "headcount_delta": SENSITIVITY_HEADCOUNT,
        "adj_months_delta": 0,
        "pct_decrease_delta": 0,
        "vac_days_delta": 0,
        "sick_days_delta": 0,
        "cm_assumption_delta": 0,
        "pm_assumption_delta": 0,
    }

    any_active = sens_config["headcount_delta"] != 0

    if not any_active:
        return dbc.Alert("Toggle at least one sensitivity parameter to see the analysis.", color="info")

    try:
        base_kwargs = {
            "regions": tuple(regions),
            "adjustments": store_data.get("adjustments", {}),
            "start_date": (
                date.fromisoformat(scenario_inputs["start_date"])
                if isinstance(scenario_inputs["start_date"], str)
                else scenario_inputs["start_date"]
            ),
            "end_date": (
                date.fromisoformat(scenario_inputs["end_date"])
                if isinstance(scenario_inputs["end_date"], str)
                else scenario_inputs["end_date"]
            ),
            "adjustment_start_date": (
                date.fromisoformat(store_data["adjustment_start_date"])
                if isinstance(store_data["adjustment_start_date"], str)
                else store_data["adjustment_start_date"]
            ),
            "pct_decrease": scenario_inputs["pct_decrease"],
            "vac_days_per_month": scenario_inputs["vac_days_per_month"],
            "sick_days_per_month": scenario_inputs["sick_days_per_month"],
            "swat_allocation": scenario_inputs.get("swat_allocation", 0),
            "excluded_projects": tuple(
                (p["CCRID"], p["EXCLUDE_FROM"]) for p in excluded_projects
            ),
            "custom_projects": tuple(
                (p["CCRID"], p["PROJECT_NAME"], p["REGION"], p["TOTAL_HOURS"], p["START_DATE"])
                for p in custom_projects
            ),
            "pm_assumption": scenario_inputs["pm_assumption"],
            "cm_assumption": scenario_inputs["cm_assumption"],
        }

        from logic.scenario import run_scenario

        def _sens_run(**kwargs):
            kw = {k: v for k, v in kwargs.items() if k not in ("pm_assumption", "cm_assumption")}
            result = run_scenario(**kw)
            result["DATE"] = pd.to_datetime(result["DATE"])
            return result

        def _sens_backlog(pm_hours, cm_hours):
            bl = _load_backlog(pm_hours, cm_hours)
            if bl.empty:
                return 0.0
            fb = bl[bl["REGION"].isin(regions)]
            if excluded_projects:
                excl_ccrids = {p["CCRID"] for p in excluded_projects}
                fb = fb[~fb["CCRID"].isin(excl_ccrids)]
            if region_filter and region_filter != "All":
                fb = fb[fb["REGION"] == region_filter]
            if selected_projects:
                fb = fb[fb["PROJECT_NAME"].isin(selected_projects)]
            return float(fb["HOUR_BACKLOG"].sum()) if not fb.empty else 0.0

        sens_result = run_sensitivity(
            base_kwargs=base_kwargs,
            sensitivity_config=sens_config,
            base_backlog=backlog,
            base_df=filtered,
            run_fn=_sens_run,
            backlog_fn=_sens_backlog,
        )

        if not sens_result.param_results:
            return dbc.Alert("No sensitivity results. Adjust the ranges.", color="info")

        children = []

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
            children.append(dcc.Graph(figure=fig_fan, config={"displayModeBar": True}))

        children.append(html.Hr())

        # Tornado chart
        fig_tornado = sensitivity_tornado_chart(
            param_results=sens_result.param_results,
            base_ending_backlog=sens_result.base_ending_backlog,
        )
        if fig_tornado:
            children.append(dcc.Graph(figure=fig_tornado, config={"displayModeBar": True}))

        children.append(html.Hr())

        # Summary table
        summary_rows = []
        for pr in sorted(
            sens_result.param_results,
            key=lambda p: abs(p.high_ending_backlog - p.low_ending_backlog),
            reverse=True,
        ):
            summary_rows.append({
                "Parameter": pr.name,
                "Low Value": f"{pr.low_value:,.2f}" if isinstance(pr.low_value, float) else str(pr.low_value),
                "Base Value": f"{pr.base_value:,.2f}" if isinstance(pr.base_value, float) else str(pr.base_value),
                "High Value": f"{pr.high_value:,.2f}" if isinstance(pr.high_value, float) else str(pr.high_value),
                "Low Backlog": f"{pr.low_ending_backlog:,.0f} hrs",
                "High Backlog": f"{pr.high_ending_backlog:,.0f} hrs",
                "Range": f"{abs(pr.high_ending_backlog - pr.low_ending_backlog):,.0f} hrs",
            })

        children.append(section_header("Sensitivity Summary"))
        children.append(dag.AgGrid(
            rowData=summary_rows,
            columnDefs=[{"field": c, "headerName": c} for c in summary_rows[0].keys()],
            defaultColDef={"sortable": True, "resizable": True},
            style={"height": "250px"},
            className="ag-theme-alpine",
        ))

        return html.Div(children)

    except Exception as exc:
        return dbc.Alert(f"Sensitivity analysis failed: {exc}", color="danger")


# ── Export callbacks ─────────────────────────────────────────────────


@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("scenario-df-store", "data"),
    State("filter-region", "value"),
    State("filter-projects", "value"),
    State("filter-month", "value"),
    State("filter-neg-gaps", "value"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, df_json, region_filter, selected_projects, month_filter, neg_gaps):
    if not df_json:
        return no_update

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])

    if region_filter and region_filter != "All":
        df = df[df["REGION"] == region_filter]
    if month_filter and month_filter != "All Months":
        df = df[df["DATE"].dt.strftime("%b %Y") == month_filter]
    if selected_projects:
        df = df[df["PROJECT_NAME"].isin(selected_projects)]
    if "neg" in (neg_gaps or []):
        df = df[df["SCENARIO_GAP"] < 0]

    df["DATE"] = df["DATE"].dt.strftime("%b %Y")
    return dcc.send_data_frame(df.to_csv, "scenario_results.csv", index=False)


@callback(
    Output("download-pptx", "data"),
    Input("btn-download-pptx", "n_clicks"),
    State("scenario-df-store", "data"),
    State("scenario-store", "data"),
    State("filter-region", "value"),
    State("filter-projects", "value"),
    State("filter-month", "value"),
    State("filter-neg-gaps", "value"),
    prevent_initial_call=True,
)
def download_pptx(n_clicks, df_json, store_data, region_filter, selected_projects, month_filter, neg_gaps):
    if not df_json or not store_data:
        return no_update

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])

    if region_filter and region_filter != "All":
        df = df[df["REGION"] == region_filter]
    if month_filter and month_filter != "All Months":
        df = df[df["DATE"].dt.strftime("%b %Y") == month_filter]
    if selected_projects:
        df = df[df["PROJECT_NAME"].isin(selected_projects)]
    if "neg" in (neg_gaps or []):
        df = df[df["SCENARIO_GAP"] < 0]

    scenario_inputs = store_data["scenario"]
    adjustment_start_date = store_data.get("adjustment_start_date")
    excluded_projects = store_data.get("excluded_projects", [])
    regions = store_data["selected_regions"]

    # Compute backlog
    backlog_df = _load_backlog(scenario_inputs["pm_assumption"], scenario_inputs["cm_assumption"])
    filtered_backlog = backlog_df if not backlog_df.empty else pd.DataFrame()
    if not filtered_backlog.empty:
        filtered_backlog = filtered_backlog[filtered_backlog["REGION"].isin(regions)]
        if excluded_projects:
            excl_ccrids = {p["CCRID"] for p in excluded_projects}
            filtered_backlog = filtered_backlog[~filtered_backlog["CCRID"].isin(excl_ccrids)]
    backlog = float(filtered_backlog["HOUR_BACKLOG"].sum()) if not filtered_backlog.empty else 0.0

    supply_delta = df["SUPPLY_DELTA"].sum()
    gap_delta = df["SCENARIO_GAP"].sum() - df["BASE_GAP"].sum()
    scenario_ending_backlog = max(backlog - df["SCENARIO_GAP"].sum(), 0.0)
    backlog_delta = scenario_ending_backlog - backlog

    region_label = scenario_inputs.get("scenario_name", "Scenario")

    base_monthly_no_backlog = _monthly_totals(df)
    base_monthly_with_backlog = _monthly_totals(df, backlog=backlog)

    fig_baseline = baseline_supply_demand_with_gap(df, region_label=region_label, monthly=base_monthly_no_backlog)
    fig_scenario = scenario_supply_demand_with_gap(
        df, region_label=region_label, monthly=base_monthly_no_backlog,
        adjustment_start_date=adjustment_start_date,
    )
    fig_gap = gap_bar_chart(df, region_label=region_label, backlog=backlog, monthly=base_monthly_with_backlog)
    fig_backlog = backlog_trend_chart(
        df, region_label=region_label, backlog=backlog,
        monthly=base_monthly_with_backlog, adjustment_start_date=adjustment_start_date,
    )

    from components.export_pptx import build_presentation

    metrics = {
        "Baseline Supply": {"value": f"{df['BASE_SUPPLY'].sum():,.0f} hrs"},
        "Scenario Supply": {"value": f"{df['SCENARIO_SUPPLY'].sum():,.0f} hrs"},
        "Total Demand": {"value": f"{df['DEMAND'].sum():,.0f} hrs"},
        "Supply Delta": {"value": f"{supply_delta:,.0f} hrs", "delta": f"{supply_delta:+,.0f} hrs"},
        "Baseline Gap": {"value": f"{df['BASE_GAP'].sum():,.0f} hrs"},
        "Scenario Gap": {"value": f"{df['SCENARIO_GAP'].sum():,.0f} hrs", "delta": f"{gap_delta:+,.0f} vs baseline"},
        "Initial Backlog": {"value": f"{backlog:,.0f} hrs"},
        "Ending Backlog": {"value": f"{scenario_ending_backlog:,.0f} hrs", "delta": f"{backlog_delta:+,.0f} hrs"},
    }

    pptx_bytes = build_presentation(
        scenario_name=region_label,
        region_label=region_label,
        metrics=metrics,
        fig_baseline=fig_baseline,
        fig_scenario=fig_scenario,
        fig_gap=fig_gap,
        fig_backlog=fig_backlog,
    )

    scenario_name = scenario_inputs.get("scenario_name", "Scenario")
    return dcc.send_bytes(pptx_bytes, f"{scenario_name.replace(' ', '_')}_results.pptx")
