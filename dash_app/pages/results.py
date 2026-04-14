"""Results page — run scenario and display charts / data."""

from __future__ import annotations

from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html

from dash_components.charts import (
    backlog_trend_chart,
    baseline_supply_demand_with_gap,
    gap_bar_chart,
    scenario_supply_demand_with_gap,
    sensitivity_fan_chart,
    sensitivity_tornado_chart,
)
from dash_components.kpi_cards import kpi_card, kpi_row
from config import (
    SENSITIVITY_ADJ_MONTHS,
    SENSITIVITY_CM_HOURS,
    SENSITIVITY_HEADCOUNT,
    SENSITIVITY_PCT_DECREASE,
    SENSITIVITY_PM_HOURS,
    SENSITIVITY_SICK_DAYS,
    SENSITIVITY_VAC_DAYS,
)
from monthly_totals import monthly_totals

dash.register_page(__name__, path="/results", name="Results")

NAVY = "#0a3370"

# ── Layout ─────────────────────────────────────────────────────────

layout = html.Div(
    [
        html.H1("Scenario Results"),
        html.Div(id="results-content"),
        dcc.Store(id="results-df-store"),
    ]
)


# ── Main content callback ──────────────────────────────────────────


@callback(
    Output("results-content", "children"),
    Input("url", "pathname"),
    State("scenario-store", "data"),
    State("projects-store", "data"),
)
def render_results(pathname, scenario_store, projects_store):
    if pathname != "/results":
        return dash.no_update

    scenario_store = scenario_store or {}
    projects_store = projects_store or {}
    scenario = scenario_store.get("scenario", {})
    regions = scenario_store.get("selected_regions", [])
    adjustments = scenario_store.get("adjustments", {})
    adj_start = scenario_store.get("adjustment_start_date")
    excluded = projects_store.get("excluded_projects", [])
    custom = projects_store.get("custom_projects", [])

    if not scenario or not regions or not adj_start or not scenario_store.get("inputs_saved"):
        return html.Div(
            "No scenario loaded. Go to Inputs, save your settings, and click Run Scenario.",
            className="alert-info-ccr",
        )

    # ── Run scenario ───────────────────────────────────────────────
    try:
        from data_adapter import get_backlog
        from logic.scenario import run_scenario

        excl_list = [{"CCRID": p["CCRID"], "EXCLUDE_FROM": p["EXCLUDE_FROM"]} for p in excluded] or None
        custom_list = [
            {
                "CCRID": p["CCRID"],
                "PROJECT_NAME": p["PROJECT_NAME"],
                "REGION": p["REGION"],
                "TOTAL_HOURS": p["TOTAL_HOURS"],
                "START_DATE": p["START_DATE"],
            }
            for p in custom
        ] or None

        df = run_scenario(
            regions=regions,
            adjustments=adjustments,
            start_date=date.fromisoformat(str(scenario["start_date"])[:10]),
            end_date=date.fromisoformat(str(scenario["end_date"])[:10]),
            adjustment_start_date=date.fromisoformat(str(adj_start)[:10]),
            pct_decrease=scenario["pct_decrease"],
            vac_days_per_month=scenario["vac_days_per_month"],
            sick_days_per_month=scenario["sick_days_per_month"],
            swat_allocation=scenario.get("swat_allocation", 0),
            excluded_projects=excl_list,
            custom_projects=custom_list,
        )
    except Exception as exc:
        return html.Div(f"Scenario failed: {exc}", className="alert-info-ccr", style={"borderColor": "#dc3545", "color": "#dc3545"})

    if df.empty:
        return html.Div("No scenario results were returned.", className="alert-info-ccr")

    df["DATE"] = pd.to_datetime(df["DATE"])

    # ── Backlog ────────────────────────────────────────────────────
    try:
        backlog_df = get_backlog(scenario["pm_assumption"], scenario["cm_assumption"]).copy()
        if not backlog_df.empty:
            backlog_df.columns = ["REGION", "PROJECT_NAME", "CCRID", "COUNT_BACKLOG", "HOUR_BACKLOG"]
            backlog_df = backlog_df[backlog_df["REGION"].isin(regions)]
            if excluded:
                excl_ccrids = {p["CCRID"] for p in excluded}
                backlog_df = backlog_df[~backlog_df["CCRID"].isin(excl_ccrids)]
        backlog = float(backlog_df["HOUR_BACKLOG"].sum()) if not backlog_df.empty else 0.0
    except Exception:
        backlog = 0.0

    # ── Build full results page ────────────────────────────────────
    region_options = [{"label": "All", "value": "All"}] + [
        {"label": r, "value": r} for r in sorted(df["REGION"].dropna().unique())
    ]
    project_options = [{"label": p, "value": p} for p in sorted(df["PROJECT_NAME"].dropna().unique())]
    month_options = [{"label": "All Months", "value": "All Months"}] + [
        {"label": m, "value": m}
        for m in sorted(df["DATE"].dt.strftime("%b %Y").unique())
    ]

    # Store the data for interactive filtering
    return html.Div(
        [
            dcc.Store(id="scenario-df", data=df.to_json(date_format="iso", orient="split")),
            dcc.Store(id="backlog-value", data=backlog),
            # Filter bar
            dbc.Row(
                [
                    dbc.Col([html.Label("Region"), dcc.Dropdown(id="filter-region", options=region_options, value="All")], md=2),
                    dbc.Col([html.Label("Project(s)"), dcc.Dropdown(id="filter-project", options=project_options, multi=True, placeholder="All projects")], md=5),
                    dbc.Col([html.Label("Month"), dcc.Dropdown(id="filter-month", options=month_options, value="All Months")], md=2),
                    dbc.Col([
                        html.Label("Options", style={"visibility": "hidden"}),
                        dbc.Checklist(
                            id="filter-neg-gaps",
                            options=[{"label": " Negative gaps only", "value": "neg"}],
                            value=[],
                            className="mt-2",
                        ),
                    ], md=3),
                ],
                className="mb-4",
            ),
            # KPI + Charts
            html.Div(id="kpi-section"),
            dcc.Tabs(
                id="chart-tabs",
                value="tab-baseline",
                className="custom-tabs mt-3",
                children=[
                    dcc.Tab(label="Baseline", value="tab-baseline", className="tab"),
                    dcc.Tab(label="Scenario", value="tab-scenario", className="tab"),
                    dcc.Tab(label="Gap Analysis", value="tab-gap", className="tab"),
                    dcc.Tab(label="Backlog Trend", value="tab-backlog", className="tab"),
                    dcc.Tab(label="Sensitivity", value="tab-sensitivity", className="tab"),
                ],
            ),
            html.Div(id="chart-content", className="mt-3"),
            # Detail data
            html.Details(
                [
                    html.Summary("Detail Data", style={"fontWeight": "600", "color": NAVY, "cursor": "pointer", "padding": "0.75rem 0"}),
                    html.Div(id="detail-data"),
                ],
                className="mt-4",
            ),
        ]
    )


# ── Callback: KPIs ────────────────────────────────────────────────


@callback(
    Output("kpi-section", "children"),
    Input("filter-region", "value"),
    Input("filter-project", "value"),
    Input("filter-month", "value"),
    Input("filter-neg-gaps", "value"),
    State("scenario-df", "data"),
    State("backlog-value", "data"),
)
def update_kpis(region, projects, month, neg_gaps, df_json, backlog):
    if not df_json:
        return dash.no_update

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])
    filtered = _apply_filters(df, region, projects, month, neg_gaps)
    backlog = float(backlog or 0)

    supply_delta = filtered["SUPPLY_DELTA"].sum()
    gap_delta = filtered["SCENARIO_GAP"].sum() - filtered["BASE_GAP"].sum()
    scenario_ending_backlog = max(backlog - filtered["SCENARIO_GAP"].sum(), 0.0)
    backlog_delta = scenario_ending_backlog - backlog

    row1 = kpi_row([
        kpi_card("Baseline Supply", f"{filtered['BASE_SUPPLY'].sum():,.0f} hrs"),
        kpi_card("Scenario Supply", f"{filtered['SCENARIO_SUPPLY'].sum():,.0f} hrs"),
        kpi_card("Total Demand", f"{filtered['DEMAND'].sum():,.0f} hrs"),
        kpi_card("Supply Delta", f"{supply_delta:,.0f} hrs", delta=f"{supply_delta:+,.0f}"),
    ])
    row2 = kpi_row([
        kpi_card("Baseline Gap", f"{filtered['BASE_GAP'].sum():,.0f} hrs"),
        kpi_card("Scenario Gap", f"{filtered['SCENARIO_GAP'].sum():,.0f} hrs", delta=f"{gap_delta:+,.0f} vs baseline"),
        kpi_card("Initial Backlog", f"{backlog:,.0f} hrs"),
        kpi_card("Ending Backlog", f"{scenario_ending_backlog:,.0f} hrs", delta=f"{backlog_delta:+,.0f}", delta_color="inverse"),
    ])

    return html.Div([
        html.H2("Supply & Demand", className="section-header"),
        row1,
        html.Div(style={"height": "0.75rem"}),
        html.H2("Gap & Backlog", className="section-header"),
        row2,
    ])


# ── Callback: Charts ──────────────────────────────────────────────


@callback(
    Output("chart-content", "children"),
    Input("chart-tabs", "value"),
    Input("filter-region", "value"),
    Input("filter-project", "value"),
    Input("filter-month", "value"),
    Input("filter-neg-gaps", "value"),
    State("scenario-df", "data"),
    State("backlog-value", "data"),
    State("scenario-store", "data"),
    State("projects-store", "data"),
)
def update_chart(tab, region, projects, month, neg_gaps, df_json, backlog, scenario_store, projects_store):
    if not df_json:
        return dash.no_update

    try:
        df = pd.read_json(df_json, orient="split")
        df["DATE"] = pd.to_datetime(df["DATE"])
        filtered = _apply_filters(df, region, projects, month, neg_gaps)
        backlog = float(backlog or 0)

        scenario_store = scenario_store or {}
        adj_start = scenario_store.get("adjustment_start_date")
        region_label = "All Selected Regions" if region == "All" else region

        monthly_no_bl = monthly_totals(filtered)
        monthly_with_bl = monthly_totals(filtered, backlog=backlog)

        if tab == "tab-baseline":
            fig = baseline_supply_demand_with_gap(filtered, region_label=region_label, monthly_df=monthly_no_bl)
            if fig:
                return dcc.Graph(figure=fig)
            return html.Div("No data to chart for the current filters.", className="alert-info-ccr")

        if tab == "tab-scenario":
            fig = scenario_supply_demand_with_gap(
                filtered, region_label=region_label, monthly_df=monthly_no_bl,
                adjustment_start_date=adj_start,
            )
            if fig:
                return dcc.Graph(figure=fig)
            return html.Div("No data to chart for the current filters.", className="alert-info-ccr")

        if tab == "tab-gap":
            fig = gap_bar_chart(filtered, region_label=region_label, backlog=backlog, monthly_df=monthly_with_bl)
            if fig:
                return dcc.Graph(figure=fig)
            return html.Div("No data to chart for the current filters.", className="alert-info-ccr")

        if tab == "tab-backlog":
            fig = backlog_trend_chart(
                filtered, region_label=region_label, backlog=backlog,
                monthly_df=monthly_with_bl, adjustment_start_date=adj_start,
            )
            if fig:
                return dcc.Graph(figure=fig)
            return html.Div("No data to chart for the current filters.", className="alert-info-ccr")

        if tab == "tab-sensitivity":
            return _sensitivity_layout(
                filtered, backlog, scenario_store, projects_store, region, projects, region_label
            )

        return html.Div()
    except Exception as exc:
        return html.Div(f"Chart error: {exc}", className="alert-info-ccr", style={"borderColor": "#dc3545", "color": "#dc3545"})


# ── Sensitivity layout + callback ──────────────────────────────────

_SENS_PARAMS = [
    ("Headcount adj.", "sens-hc", SENSITIVITY_HEADCOUNT, -50, 50, True),
    ("Adj. month", "sens-adj-mo", SENSITIVITY_ADJ_MONTHS, 1, 12, False),
    ("Non-project %", "sens-pct", SENSITIVITY_PCT_DECREASE, 1, 50, False),
    ("Vacation days", "sens-vac", SENSITIVITY_VAC_DAYS, 1, 30, False),
    ("Sick days", "sens-sick", SENSITIVITY_SICK_DAYS, 1, 30, False),
    ("CM hours", "sens-cm", SENSITIVITY_CM_HOURS, 1, 15, False),
    ("PM hours", "sens-pm", SENSITIVITY_PM_HOURS, 1, 15, False),
]


def _sensitivity_layout(filtered, backlog, scenario_store, projects_store, region, sel_projects, region_label):
    """Build the sensitivity tab content with controls and run analysis inline."""
    scenario = scenario_store.get("scenario", {})
    regions = scenario_store.get("selected_regions", [])
    adjustments = scenario_store.get("adjustments", {})
    adj_start = scenario_store.get("adjustment_start_date")
    excluded = (projects_store or {}).get("excluded_projects", [])
    custom = (projects_store or {}).get("custom_projects", [])

    # Default config with all defaults active
    sens_config = {
        "enabled": True,
        "headcount_delta": SENSITIVITY_HEADCOUNT,
        "adj_months_delta": SENSITIVITY_ADJ_MONTHS,
        "pct_decrease_delta": SENSITIVITY_PCT_DECREASE / 100,
        "vac_days_delta": SENSITIVITY_VAC_DAYS / 12,
        "sick_days_delta": SENSITIVITY_SICK_DAYS / 12,
        "cm_assumption_delta": SENSITIVITY_CM_HOURS,
        "pm_assumption_delta": SENSITIVITY_PM_HOURS,
    }

    any_active = any(v != 0 for v in [
        sens_config["headcount_delta"],
        sens_config["pct_decrease_delta"],
        sens_config["vac_days_delta"],
        sens_config["sick_days_delta"],
        sens_config["cm_assumption_delta"],
        sens_config["pm_assumption_delta"],
        sens_config["adj_months_delta"],
    ])

    if not any_active:
        return html.Div("Toggle at least one sensitivity parameter to see the analysis.", className="alert-info-ccr")

    # Run sensitivity
    try:
        import logic.sensitivity as sens_mod
        from monthly_totals import monthly_totals as mt_fn

        # Patch sensitivity module to use our monthly_totals
        sens_mod._monthly_totals = mt_fn

        from data_adapter import get_backlog as da_get_backlog
        from logic.scenario import run_scenario

        base_kwargs = {
            "regions": tuple(regions),
            "adjustments": adjustments,
            "start_date": date.fromisoformat(str(scenario["start_date"])[:10]),
            "end_date": date.fromisoformat(str(scenario["end_date"])[:10]),
            "adjustment_start_date": date.fromisoformat(str(adj_start)[:10]),
            "pct_decrease": scenario["pct_decrease"],
            "vac_days_per_month": scenario["vac_days_per_month"],
            "sick_days_per_month": scenario["sick_days_per_month"],
            "excluded_projects": tuple(
                (p["CCRID"], p["EXCLUDE_FROM"]) for p in excluded
            ),
            "custom_projects": tuple(
                (p["CCRID"], p["PROJECT_NAME"], p["REGION"], p["TOTAL_HOURS"], p["START_DATE"])
                for p in custom
            ),
            "pm_assumption": scenario["pm_assumption"],
            "cm_assumption": scenario["cm_assumption"],
            "swat_allocation": scenario.get("swat_allocation", 0),
        }

        def _sens_run(**kwargs):
            kw = {k: v for k, v in kwargs.items() if k not in ("pm_assumption", "cm_assumption")}
            result = run_scenario(
                regions=list(kw.pop("regions")),
                excluded_projects=[{"CCRID": e[0], "EXCLUDE_FROM": e[1]} for e in kw.pop("excluded_projects", ())] or None,
                custom_projects=[
                    {"CCRID": c[0], "PROJECT_NAME": c[1], "REGION": c[2], "TOTAL_HOURS": c[3], "START_DATE": c[4]}
                    for c in kw.pop("custom_projects", ())
                ] or None,
                **kw,
            )
            result["DATE"] = pd.to_datetime(result["DATE"])
            return result

        def _sens_backlog(pm_hours, cm_hours):
            bl = da_get_backlog(pm_hours, cm_hours).copy()
            if bl.empty:
                return 0.0
            bl.columns = ["REGION", "PROJECT_NAME", "CCRID", "COUNT_BACKLOG", "HOUR_BACKLOG"]
            fb = bl[bl["REGION"].isin(regions)]
            if excluded:
                excl_ccrids = {p["CCRID"] for p in excluded}
                fb = fb[~fb["CCRID"].isin(excl_ccrids)]
            if region != "All":
                fb = fb[fb["REGION"] == region]
            if sel_projects:
                fb = fb[fb["PROJECT_NAME"].isin(sel_projects)]
            return float(fb["HOUR_BACKLOG"].sum()) if not fb.empty else 0.0

        sens_result = sens_mod.run_sensitivity(
            base_kwargs=base_kwargs,
            sensitivity_config=sens_config,
            base_backlog=backlog,
            base_df=filtered,
            run_fn=_sens_run,
            backlog_fn=_sens_backlog,
        )

    except Exception as exc:
        return html.Div(f"Sensitivity analysis failed: {exc}", className="alert-info-ccr", style={"borderColor": "#dc3545"})

    if not sens_result.param_results:
        return html.Div("No sensitivity results. Adjust the ranges above.", className="alert-info-ccr")

    # Build charts
    children = []

    fig_fan = sensitivity_fan_chart(
        base_monthly=sens_result.base_monthly,
        envelope_min=sens_result.envelope_min,
        envelope_max=sens_result.envelope_max,
        param_results=sens_result.param_results,
        region_label=region_label,
        adjustment_start_date=adj_start,
    )
    if fig_fan:
        children.append(html.P(
            f"Shaded area shows the range of possible backlog outcomes. "
            f"Base ending backlog: {sens_result.base_ending_backlog:,.0f} hrs.",
            className="section-subtitle",
        ))
        children.append(dcc.Graph(figure=fig_fan))

    children.append(html.Hr())

    fig_tornado = sensitivity_tornado_chart(
        param_results=sens_result.param_results,
        base_ending_backlog=sens_result.base_ending_backlog,
    )
    if fig_tornado:
        children.append(html.P(
            "Bars show the impact of each input on ending backlog. Wider bars indicate higher sensitivity.",
            className="section-subtitle",
        ))
        children.append(dcc.Graph(figure=fig_tornado))

    children.append(html.Hr())

    # Summary table
    children.append(html.H3("Sensitivity Summary", className="section-header"))
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
    children.append(dash_table.DataTable(
        data=summary_rows,
        columns=[{"name": c, "id": c} for c in ["Parameter", "Low Value", "Base Value", "High Value", "Low Backlog", "High Backlog", "Range"]],
        style_header={"backgroundColor": NAVY, "color": "white", "fontWeight": "600"},
        style_cell={"fontFamily": "Tahoma", "fontSize": "0.85rem", "textAlign": "center"},
    ))

    return html.Div(children)


# ── Callback: Detail data ──────────────────────────────────────────


@callback(
    Output("detail-data", "children"),
    Input("filter-region", "value"),
    Input("filter-project", "value"),
    Input("filter-month", "value"),
    Input("filter-neg-gaps", "value"),
    State("scenario-df", "data"),
)
def update_detail(region, projects, month, neg_gaps, df_json):
    if not df_json:
        return dash.no_update

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])
    filtered = _apply_filters(df, region, projects, month, neg_gaps)

    display = filtered.assign(DATE=filtered["DATE"].dt.strftime("%b %Y"))

    return html.Div(
        [
            html.P(f"{len(filtered):,} of {len(df):,} rows", className="section-subtitle"),
            html.Button(
                "Download CSV",
                id="btn-download-csv",
                className="btn-download mb-2",
            ),
            dcc.Download(id="download-csv"),
            dash_table.DataTable(
                data=display.to_dict("records"),
                columns=[{"name": c, "id": c} for c in display.columns],
                style_header={"backgroundColor": NAVY, "color": "white", "fontWeight": "600"},
                style_cell={"fontFamily": "Tahoma", "fontSize": "0.8rem"},
                page_size=20,
                sort_action="native",
                filter_action="native",
            ),
        ]
    )


@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("scenario-df", "data"),
    State("filter-region", "value"),
    State("filter-project", "value"),
    State("filter-month", "value"),
    State("filter-neg-gaps", "value"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, df_json, region, projects, month, neg_gaps):
    if not n_clicks or not df_json:
        return dash.no_update

    df = pd.read_json(df_json, orient="split")
    df["DATE"] = pd.to_datetime(df["DATE"])
    filtered = _apply_filters(df, region, projects, month, neg_gaps)
    display = filtered.assign(DATE=filtered["DATE"].dt.strftime("%b %Y"))
    return dcc.send_data_frame(display.to_csv, "scenario_results.csv", index=False)


# ── Helpers ────────────────────────────────────────────────────────


def _apply_filters(df, region, projects, month, neg_gaps):
    filtered = df
    if region and region != "All":
        filtered = filtered[filtered["REGION"] == region]
    if month and month != "All Months":
        filtered = filtered[filtered["DATE"].dt.strftime("%b %Y") == month]
    if projects:
        filtered = filtered[filtered["PROJECT_NAME"].isin(projects)]
    if neg_gaps and "neg" in neg_gaps:
        filtered = filtered[filtered["SCENARIO_GAP"] < 0]
    return filtered
