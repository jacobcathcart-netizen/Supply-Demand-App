"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import base64
import io
import json
from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, callback, dash_table, dcc, html

from config import (
    DEFAULT_CM_HOURS,
    DEFAULT_END_DATE,
    DEFAULT_PCT_DECREASE,
    DEFAULT_PM_HOURS,
    DEFAULT_SICK_DAYS_PER_YEAR,
    DEFAULT_START_DATE,
    DEFAULT_VAC_DAYS_PER_YEAR,
    SWAT,
)

dash.register_page(__name__, path="/inputs", name="Inputs")

# ── Helpers ────────────────────────────────────────────────────────

NAVY = "#0a3370"
LIGHT_BLUE = "#008bc1"


def _section_header(title: str, subtitle: str | None = None) -> html.Div:
    children = [html.H3(title, className="section-header")]
    if subtitle:
        children.append(html.P(subtitle, className="section-subtitle"))
    return html.Div(children)


# ── Layout ─────────────────────────────────────────────────────────

layout = html.Div(
    [
        html.H1("Scenario Inputs"),
        dcc.Tabs(
            id="inputs-tabs",
            value="tab-params",
            className="custom-tabs",
            children=[
                dcc.Tab(label="Scenario Parameters", value="tab-params", className="tab"),
                dcc.Tab(label="Projects", value="tab-projects", className="tab"),
            ],
        ),
        html.Div(id="inputs-tab-content"),
    ]
)


# ── Tab rendering ──────────────────────────────────────────────────


@callback(
    Output("inputs-tab-content", "children"),
    Input("inputs-tabs", "value"),
    State("scenario-store", "data"),
    State("projects-store", "data"),
)
def render_tab(tab, scenario_store, projects_store):
    scenario_store = scenario_store or {}
    projects_store = projects_store or {}
    scenario = scenario_store.get("scenario", {})

    if tab == "tab-params":
        return _params_tab(scenario_store, scenario)
    return _projects_tab(scenario_store, projects_store, scenario)


def _params_tab(scenario_store, scenario):
    selected_regions = scenario_store.get("selected_regions", [])
    adjustments = scenario_store.get("adjustments", {})

    # Fetch regions
    try:
        from data_adapter import get_regions_df
        regions_df = get_regions_df()
        regions_list = regions_df["REGION"].dropna().astype(str).sort_values().tolist() if not regions_df.empty else []
    except Exception:
        regions_list = []

    # Build adjustment inputs
    adj_children = []
    target_regions = selected_regions if selected_regions else []
    for region in target_regions:
        adj_children.append(
            dbc.Col(
                [
                    html.Label(region, style={"fontSize": "0.82rem"}),
                    dcc.Input(
                        id={"type": "hc-adj", "region": region},
                        type="number",
                        value=int(adjustments.get(region, 0)),
                        min=-100,
                        step=1,
                        className="dash-input",
                        style={"width": "100%"},
                    ),
                ],
                xs=6, md=4, className="mb-2",
            )
        )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Scenario name"),
                            dcc.Input(
                                id="scenario-name",
                                type="text",
                                value=scenario.get("scenario_name", "Scenario 1"),
                                className="dash-input",
                                style={"width": "100%"},
                            ),
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        [
                            html.Label("Regions"),
                            dcc.Dropdown(
                                id="region-selector",
                                options=[{"label": r, "value": r} for r in regions_list],
                                value=selected_regions,
                                multi=True,
                                placeholder="Select regions...",
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    # Left column: assumptions
                    dbc.Col(
                        [
                            _section_header("Date Range"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Start date"),
                                            dcc.DatePickerSingle(
                                                id="start-date",
                                                date=scenario.get("start_date", DEFAULT_START_DATE.isoformat()),
                                                display_format="MM/DD/YYYY",
                                            ),
                                        ],
                                        md=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("End date"),
                                            dcc.DatePickerSingle(
                                                id="end-date",
                                                date=scenario.get("end_date", DEFAULT_END_DATE.isoformat()),
                                                display_format="MM/DD/YYYY",
                                            ),
                                        ],
                                        md=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            _section_header("Workforce Assumptions"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Non-project (%)"),
                                            dcc.Input(
                                                id="pct-decrease",
                                                type="number",
                                                value=int(scenario.get("pct_decrease", DEFAULT_PCT_DECREASE) * 100),
                                                min=0, max=100, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Vacation days / year"),
                                            dcc.Input(
                                                id="vac-days",
                                                type="number",
                                                value=int(round(scenario.get("vac_days_per_month", DEFAULT_VAC_DAYS_PER_YEAR / 12) * 12)),
                                                min=0, max=365, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Sick days / year"),
                                            dcc.Input(
                                                id="sick-days",
                                                type="number",
                                                value=int(round(scenario.get("sick_days_per_month", DEFAULT_SICK_DAYS_PER_YEAR / 12) * 12)),
                                                min=0, max=365, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            _section_header("SWAT Allocation"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("SWAT Headcount"),
                                            dcc.Input(
                                                id="swat-allocation",
                                                type="number",
                                                value=int(scenario.get("swat_allocation", SWAT)),
                                                min=0, max=100, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            _section_header("Backlog Assumptions"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Hours / CM item"),
                                            dcc.Input(
                                                id="cm-hours",
                                                type="number",
                                                value=int(scenario.get("cm_assumption", DEFAULT_CM_HOURS)),
                                                min=0, max=30, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Hours / PM item"),
                                            dcc.Input(
                                                id="pm-hours",
                                                type="number",
                                                value=int(scenario.get("pm_assumption", DEFAULT_PM_HOURS)),
                                                min=0, max=30, step=1,
                                                className="dash-input",
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                        md=6,
                    ),
                    # Right column: adjustments
                    dbc.Col(
                        [
                            _section_header("Headcount Adjustments"),
                            html.Div(
                                [
                                    html.Label("Adjustment start date"),
                                    dcc.DatePickerSingle(
                                        id="adj-start-date",
                                        date=scenario_store.get(
                                            "adjustment_start_date",
                                            scenario.get("start_date", DEFAULT_START_DATE.isoformat()),
                                        ),
                                        display_format="MM/DD/YYYY",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                dbc.Row(adj_children, className="g-2") if adj_children
                                else html.P(
                                    "Select at least one region above to configure adjustments.",
                                    className="section-subtitle",
                                ),
                                id="adj-container",
                            ),
                        ],
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            # Save button
            dbc.Row(
                dbc.Col(
                    html.Button(
                        "Save & Continue",
                        id="btn-save-inputs",
                        className="btn-ccr-primary",
                    ),
                    md=4,
                    className="mx-auto",
                ),
                className="mb-3",
            ),
            html.Div(id="save-feedback"),
            # Run button
            dbc.Row(
                dbc.Col(
                    dcc.Link(
                        html.Button("Run Scenario", id="btn-run", className="btn-ccr-primary"),
                        href="/results",
                        style={"textDecoration": "none", "display": "block"},
                    ),
                    md=4,
                    className="mx-auto",
                ),
                className="mb-4",
            ),
            # Backlog preview
            html.Details(
                [
                    html.Summary(
                        "Backlog Preview",
                        style={"fontWeight": "600", "color": NAVY, "cursor": "pointer", "padding": "0.75rem 0"},
                    ),
                    html.Div(id="backlog-preview-content"),
                ],
            ),
        ],
        className="mt-3",
    )


def _projects_tab(scenario_store, projects_store, scenario):
    excluded = projects_store.get("excluded_projects", [])
    custom = projects_store.get("custom_projects", [])
    selected_regions = scenario_store.get("selected_regions", [])

    return html.Div(
        [
            _section_header("Manage Projects", "Exclude existing projects or add custom ones"),
            html.Hr(),
            # ── Remove projects ────────────────────────────────────
            _section_header("Remove Projects", "Excluded projects are removed from demand and supply allocation"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(id="excl-filter-region", multi=True, placeholder="Filter by Region"),
                        md=4,
                    ),
                    dbc.Col(
                        dcc.Dropdown(id="excl-filter-customer", multi=True, placeholder="Filter by Customer"),
                        md=4,
                    ),
                    dbc.Col(
                        dcc.Dropdown(id="excl-filter-state", multi=True, placeholder="Filter by State"),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(id="excl-project-select", multi=True, placeholder="Select projects to exclude..."),
                        md=8,
                    ),
                    dbc.Col(
                        [
                            html.Label("Exclude From"),
                            dcc.DatePickerSingle(
                                id="excl-date",
                                date=scenario.get("start_date", DEFAULT_START_DATE.isoformat()),
                                display_format="MM/DD/YYYY",
                            ),
                        ],
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Button("Add Exclusion(s)", id="btn-add-exclusion", className="btn-ccr-primary"),
                        md=4,
                    ),
                    dbc.Col(
                        html.Button("Exclude All Filtered", id="btn-exclude-all", className="btn-ccr-secondary"),
                        md=4,
                    ),
                ],
                className="mb-3 g-2",
            ),
            html.Div(id="exclusions-table"),
            html.Hr(),
            # ── Add projects ───────────────────────────────────────
            _section_header("Add Projects", "Add hypothetical demand-only projects. Hours are spread evenly across scenario months from the start date."),
            dcc.RadioItems(
                id="add-mode",
                options=[
                    {"label": " Manual Entry", "value": "manual"},
                    {"label": " CSV Upload", "value": "csv"},
                ],
                value="manual",
                inline=True,
                className="mb-3",
                inputStyle={"marginRight": "4px"},
            ),
            html.Div(id="add-project-content"),
            html.Div(id="custom-projects-table"),
            # Hidden stores for exclusion filter state
            dcc.Store(id="excl-available-projects"),
        ],
        className="mt-3",
    )


# ── Callbacks: Exclusion filters ───────────────────────────────────


@callback(
    Output("excl-filter-region", "options"),
    Output("excl-filter-customer", "options"),
    Output("excl-filter-state", "options"),
    Output("excl-available-projects", "data"),
    Input("inputs-tabs", "value"),
    State("scenario-store", "data"),
    State("projects-store", "data"),
)
def load_project_filters(tab, scenario_store, projects_store):
    if tab != "tab-projects":
        return [], [], [], []

    scenario_store = scenario_store or {}
    projects_store = projects_store or {}
    selected_regions = scenario_store.get("selected_regions", [])

    try:
        from data_adapter import get_demand_weight, get_projects
        projects_df = get_projects()
        weights_df = get_demand_weight()
        dataset_ccrids = set(weights_df["CCRID"].unique())
        in_dataset = projects_df[projects_df["CCRID"].isin(dataset_ccrids)].copy()
        if selected_regions:
            in_dataset = in_dataset[in_dataset["REGION"].isin(selected_regions)]
    except Exception:
        return [], [], [], []

    if in_dataset.empty:
        return [], [], [], []

    region_opts = [{"label": r, "value": r} for r in sorted(in_dataset["REGION"].dropna().unique())]
    customer_opts = [{"label": c, "value": c} for c in sorted(in_dataset["CUSTOMER"].dropna().unique())]
    state_opts = [{"label": s, "value": s} for s in sorted(in_dataset["STATE"].dropna().unique())]

    projects_json = in_dataset[["CCRID", "PROJECT_NAME", "REGION", "CUSTOMER", "STATE"]].drop_duplicates("CCRID").to_dict("records")
    return region_opts, customer_opts, state_opts, projects_json


@callback(
    Output("excl-project-select", "options"),
    Input("excl-filter-region", "value"),
    Input("excl-filter-customer", "value"),
    Input("excl-filter-state", "value"),
    State("excl-available-projects", "data"),
    State("projects-store", "data"),
)
def update_project_options(filter_region, filter_customer, filter_state, all_projects, projects_store):
    if not all_projects:
        return []

    projects_store = projects_store or {}
    excluded_ccrids = {p["CCRID"] for p in projects_store.get("excluded_projects", [])}

    df = pd.DataFrame(all_projects)
    if filter_region:
        df = df[df["REGION"].isin(filter_region)]
    if filter_customer:
        df = df[df["CUSTOMER"].isin(filter_customer)]
    if filter_state:
        df = df[df["STATE"].isin(filter_state)]

    df = df[~df["CCRID"].isin(excluded_ccrids)]
    return [
        {"label": f"{row['PROJECT_NAME']} ({row['CCRID']})", "value": row["CCRID"]}
        for _, row in df.iterrows()
    ]


# ── Callback: Add exclusion ───────────────────────────────────────


@callback(
    Output("projects-store", "data", allow_duplicate=True),
    Input("btn-add-exclusion", "n_clicks"),
    Input("btn-exclude-all", "n_clicks"),
    State("excl-project-select", "value"),
    State("excl-project-select", "options"),
    State("excl-date", "date"),
    State("projects-store", "data"),
    State("excl-available-projects", "data"),
    State("excl-filter-region", "value"),
    State("excl-filter-customer", "value"),
    State("excl-filter-state", "value"),
    prevent_initial_call=True,
)
def add_exclusions(add_clicks, all_clicks, selected_ccrids, options, excl_date, projects_store, all_projects, fr, fc, fs):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    projects_store = projects_store or {}
    excluded = list(projects_store.get("excluded_projects", []))

    label_map = {o["value"]: o["label"] for o in (options or [])}

    if btn_id == "btn-add-exclusion" and selected_ccrids:
        for ccrid in selected_ccrids:
            excluded.append({
                "CCRID": ccrid,
                "PROJECT_NAME": label_map.get(ccrid, ccrid),
                "EXCLUDE_FROM": str(excl_date),
            })
    elif btn_id == "btn-exclude-all" and all_projects:
        existing_ccrids = {p["CCRID"] for p in excluded}
        df = pd.DataFrame(all_projects)
        if fr:
            df = df[df["REGION"].isin(fr)]
        if fc:
            df = df[df["CUSTOMER"].isin(fc)]
        if fs:
            df = df[df["STATE"].isin(fs)]
        for _, row in df.iterrows():
            if row["CCRID"] not in existing_ccrids:
                excluded.append({
                    "CCRID": row["CCRID"],
                    "PROJECT_NAME": f"{row['PROJECT_NAME']} ({row['CCRID']})",
                    "EXCLUDE_FROM": str(excl_date),
                })

    projects_store["excluded_projects"] = excluded
    return projects_store


# ── Callback: Display exclusions table ─────────────────────────────


@callback(
    Output("exclusions-table", "children"),
    Input("projects-store", "data"),
)
def display_exclusions(projects_store):
    projects_store = projects_store or {}
    excluded = projects_store.get("excluded_projects", [])
    if not excluded:
        return html.Div()

    return html.Div(
        [
            html.Hr(),
            _section_header("Excluded Projects", f"{len(excluded)} project(s) excluded"),
            dash_table.DataTable(
                data=excluded,
                columns=[
                    {"name": "CCRID", "id": "CCRID"},
                    {"name": "Project Name", "id": "PROJECT_NAME"},
                    {"name": "Exclude From", "id": "EXCLUDE_FROM"},
                ],
                style_header={"backgroundColor": NAVY, "color": "white", "fontWeight": "600"},
                style_cell={"fontFamily": "Tahoma", "fontSize": "0.85rem"},
            ),
            html.Button(
                "Clear All Exclusions",
                id="btn-clear-exclusions",
                className="btn-ccr-secondary mt-2",
            ),
        ]
    )


@callback(
    Output("projects-store", "data", allow_duplicate=True),
    Input("btn-clear-exclusions", "n_clicks"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def clear_exclusions(n_clicks, projects_store):
    if not n_clicks:
        return dash.no_update
    projects_store = projects_store or {}
    projects_store["excluded_projects"] = []
    return projects_store


# ── Callback: Add project mode toggle ──────────────────────────────


@callback(
    Output("add-project-content", "children"),
    Input("add-mode", "value"),
    State("scenario-store", "data"),
)
def render_add_mode(mode, scenario_store):
    scenario_store = scenario_store or {}
    scenario = scenario_store.get("scenario", {})

    try:
        from data_adapter import get_regions_df
        regions_list = get_regions_df()["REGION"].dropna().astype(str).sort_values().tolist()
    except Exception:
        regions_list = []

    if mode == "manual":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col([html.Label("Project Name"), dcc.Input(id="new-proj-name", type="text", className="dash-input", style={"width": "100%"})], md=3),
                        dbc.Col([html.Label("Region"), dcc.Dropdown(id="new-proj-region", options=[{"label": r, "value": r} for r in regions_list])], md=3),
                        dbc.Col([html.Label("Total Hours"), dcc.Input(id="new-proj-hours", type="number", value=0, min=0, step=100, className="dash-input", style={"width": "100%"})], md=3),
                        dbc.Col([html.Label("Start Date"), dcc.DatePickerSingle(id="new-proj-start", date=scenario.get("start_date", DEFAULT_START_DATE.isoformat()), display_format="MM/DD/YYYY")], md=3),
                    ],
                    className="mb-3",
                ),
                html.Button("Add Project", id="btn-add-project", className="btn-ccr-primary"),
                # Hidden elements to prevent callback errors
                dcc.Upload(id="csv-upload", style={"display": "none"}),
            ],
            className="mb-3",
        )

    return html.Div(
        [
            html.P(
                "CSV must contain columns: CCRID, PROJECT_NAME, REGION, TOTAL_HOURS, START_DATE (YYYY-MM-DD).",
                className="section-subtitle",
            ),
            dcc.Upload(
                id="csv-upload",
                children=html.Div(["Drag and Drop or ", html.A("Select CSV File")]),
                style={
                    "width": "100%", "height": "60px", "lineHeight": "60px",
                    "borderWidth": "1px", "borderStyle": "dashed", "borderRadius": "8px",
                    "borderColor": "#D9DDE5", "textAlign": "center", "cursor": "pointer",
                },
                accept=".csv",
            ),
            # Hidden elements to prevent callback errors
            dcc.Input(id="new-proj-name", type="hidden"),
            dcc.Input(id="new-proj-region", type="hidden"),
            dcc.Input(id="new-proj-hours", type="hidden"),
            dcc.DatePickerSingle(id="new-proj-start", style={"display": "none"}),
            html.Button(id="btn-add-project", style={"display": "none"}),
        ],
        className="mb-3",
    )


# ── Callback: Add custom project (manual) ─────────────────────────


@callback(
    Output("projects-store", "data", allow_duplicate=True),
    Input("btn-add-project", "n_clicks"),
    State("new-proj-name", "value"),
    State("new-proj-region", "value"),
    State("new-proj-hours", "value"),
    State("new-proj-start", "date"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def add_manual_project(n_clicks, name, region, hours, start_date, projects_store):
    if not n_clicks or not name or not name.strip():
        return dash.no_update

    projects_store = projects_store or {}
    custom = list(projects_store.get("custom_projects", []))
    counter = len(custom) + 1
    custom.append({
        "CCRID": f"CUSTOM_{counter:03d}",
        "PROJECT_NAME": name.strip(),
        "REGION": region,
        "TOTAL_HOURS": hours or 0,
        "START_DATE": str(start_date),
    })
    projects_store["custom_projects"] = custom
    return projects_store


# ── Callback: Add custom project (CSV) ────────────────────────────


@callback(
    Output("projects-store", "data", allow_duplicate=True),
    Input("csv-upload", "contents"),
    State("csv-upload", "filename"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def add_csv_projects(contents, filename, projects_store):
    if contents is None:
        return dash.no_update

    projects_store = projects_store or {}
    custom = list(projects_store.get("custom_projects", []))

    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    csv_df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

    required_cols = {"CCRID", "PROJECT_NAME", "REGION", "TOTAL_HOURS", "START_DATE"}
    if not required_cols.issubset(set(csv_df.columns)):
        return dash.no_update

    existing_ccrids = {p["CCRID"] for p in custom}
    new_projects = csv_df[list(required_cols)].to_dict("records")
    for p in new_projects:
        if p["CCRID"] not in existing_ccrids:
            custom.append(p)
            existing_ccrids.add(p["CCRID"])

    projects_store["custom_projects"] = custom
    return projects_store


# ── Callback: Display custom projects ──────────────────────────────


@callback(
    Output("custom-projects-table", "children"),
    Input("projects-store", "data"),
)
def display_custom(projects_store):
    projects_store = projects_store or {}
    custom = projects_store.get("custom_projects", [])
    if not custom:
        return html.Div()

    return html.Div(
        [
            html.Hr(),
            _section_header("Custom Projects", f"{len(custom)} project(s) added"),
            dash_table.DataTable(
                data=custom,
                columns=[
                    {"name": c, "id": c}
                    for c in ["CCRID", "PROJECT_NAME", "REGION", "TOTAL_HOURS", "START_DATE"]
                ],
                style_header={"backgroundColor": NAVY, "color": "white", "fontWeight": "600"},
                style_cell={"fontFamily": "Tahoma", "fontSize": "0.85rem"},
            ),
            html.Button(
                "Clear All Custom Projects",
                id="btn-clear-custom",
                className="btn-ccr-secondary mt-2",
            ),
        ]
    )


@callback(
    Output("projects-store", "data", allow_duplicate=True),
    Input("btn-clear-custom", "n_clicks"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def clear_custom(n_clicks, projects_store):
    if not n_clicks:
        return dash.no_update
    projects_store = projects_store or {}
    projects_store["custom_projects"] = []
    return projects_store


# ── Callback: Save inputs ─────────────────────────────────────────


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Output("save-feedback", "children"),
    Input("btn-save-inputs", "n_clicks"),
    State("scenario-name", "value"),
    State("region-selector", "value"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("pct-decrease", "value"),
    State("vac-days", "value"),
    State("sick-days", "value"),
    State("cm-hours", "value"),
    State("pm-hours", "value"),
    State("swat-allocation", "value"),
    State("adj-start-date", "date"),
    State({"type": "hc-adj", "region": ALL}, "value"),
    State({"type": "hc-adj", "region": ALL}, "id"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def save_inputs(
    n_clicks, name, regions, start_date, end_date,
    pct, vac, sick, cm, pm, swat, adj_start,
    adj_values, adj_ids, current_store,
):
    if not n_clicks:
        return dash.no_update, dash.no_update

    errors = []
    if not regions:
        errors.append("Select at least one region.")
    if start_date and end_date and start_date > end_date:
        errors.append("Start date must be before end date.")

    if errors:
        return dash.no_update, html.Div(
            [html.Div(e, className="alert-info-ccr mb-1", style={"borderColor": "#dc3545", "color": "#dc3545"}) for e in errors]
        )

    adjustments = {}
    if adj_ids and adj_values:
        for id_dict, val in zip(adj_ids, adj_values):
            adjustments[id_dict["region"]] = int(val or 0)

    # Normalize adjustment start date to first of month
    adj_start_str = adj_start
    if adj_start:
        adj_date = date.fromisoformat(str(adj_start)[:10])
        adj_start_str = adj_date.replace(day=1).isoformat()

    store = {
        "inputs_saved": True,
        "scenario": {
            "scenario_name": name or "Scenario 1",
            "pct_decrease": (pct or 0) / 100,
            "vac_days_per_month": (vac or 0) / 12,
            "sick_days_per_month": (sick or 0) / 12,
            "start_date": start_date,
            "end_date": end_date,
            "pm_assumption": pm or DEFAULT_PM_HOURS,
            "cm_assumption": cm or DEFAULT_CM_HOURS,
            "swat_allocation": swat or SWAT,
        },
        "selected_regions": regions or [],
        "adjustments": adjustments,
        "adjustment_start_date": adj_start_str,
    }

    return store, html.Span("Inputs saved!", className="status-badge", style={"borderColor": "#28a745", "color": "#28a745"})


# ── Callback: Backlog preview ──────────────────────────────────────


@callback(
    Output("backlog-preview-content", "children"),
    Input("btn-save-inputs", "n_clicks"),
    Input("inputs-tabs", "value"),
    State("cm-hours", "value"),
    State("pm-hours", "value"),
)
def backlog_preview(n_clicks, tab, cm, pm):
    if tab != "tab-params":
        return html.Div()

    cm = cm or DEFAULT_CM_HOURS
    pm = pm or DEFAULT_PM_HOURS

    try:
        from data_adapter import get_backlog, get_cm_backlog, get_pm_backlog
        from dash_components.charts import backlog_by_region_chart, pm_cm_breakdown_chart

        backlog_df = get_backlog(pm, cm)
        if backlog_df.empty:
            return html.Div("No backlog data available.", className="alert-info-ccr")

        for col in ("COUNT", "HOURS"):
            if col in backlog_df.columns:
                backlog_df[col] = pd.to_numeric(backlog_df[col], errors="coerce").fillna(0)

        pm_df = get_pm_backlog()
        cm_df = get_cm_backlog()
        pm_df["COUNT"] = pd.to_numeric(pm_df["COUNT"], errors="coerce").fillna(0)
        cm_df["COUNT"] = pd.to_numeric(cm_df["COUNT"], errors="coerce").fillna(0)
        pm_items = int(pm_df["COUNT"].sum())
        cm_items = int(cm_df["COUNT"].sum())

        total_items = int(backlog_df["COUNT"].sum())
        total_hours = backlog_df["HOURS"].sum()
        n_regions = backlog_df["REGION"].nunique()
        n_projects = backlog_df["CCRID"].nunique()

        from dash_components.kpi_cards import kpi_card, kpi_row

        metrics = kpi_row([
            kpi_card("Total Jobs", f"{total_items:,}"),
            kpi_card("Total Hours", f"{total_hours:,.0f}"),
            kpi_card("PM Jobs", f"{pm_items:,}", delta=f"{pm_items * pm:,.0f} hrs"),
            kpi_card("CM Jobs", f"{cm_items:,}", delta=f"{cm_items * cm:,.0f} hrs"),
        ])

        by_region = (
            backlog_df.groupby("REGION", as_index=False)
            .agg(ITEMS=("COUNT", "sum"), HOURS=("HOURS", "sum"))
            .sort_values("HOURS", ascending=True)
        )
        fig1 = backlog_by_region_chart(by_region)

        # PM vs CM breakdown
        pm_by_r = pm_df.groupby("REGION", as_index=False)["COUNT"].sum().rename(columns={"COUNT": "PM"})
        cm_by_r = cm_df.groupby("REGION", as_index=False)["COUNT"].sum().rename(columns={"COUNT": "CM"})
        breakdown = pm_by_r.merge(cm_by_r, on="REGION", how="outer").fillna(0)
        breakdown["PM_HRS"] = breakdown["PM"] * pm
        breakdown["CM_HRS"] = breakdown["CM"] * cm
        fig2 = pm_cm_breakdown_chart(breakdown.sort_values("REGION"))

        return html.Div(
            [
                metrics,
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig1), md=6),
                        dbc.Col(dcc.Graph(figure=fig2), md=6),
                    ],
                    className="mt-3",
                ),
            ]
        )

    except Exception as exc:
        return html.Div(f"Could not load backlog data: {exc}", className="alert-info-ccr")
