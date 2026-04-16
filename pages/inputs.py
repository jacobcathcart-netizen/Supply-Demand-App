"""Inputs page — configure and save scenario parameters."""

from __future__ import annotations

import base64
import io
from datetime import date

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import callback, dcc, html, Input, Output, State, no_update

from components.branding import NAVY, section_header
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

dash.register_page(__name__, path="/inputs", name="Inputs", order=1)

# ── Helpers ──────────────────────────────────────────────────────────


def _get_regions() -> list[str]:
    try:
        from data.snowflake import get_regions_df
        df = get_regions_df()
        if df.empty or "REGION" not in df.columns:
            return []
        return sorted(df["REGION"].dropna().astype(str).tolist())
    except Exception:
        return []


def _get_projects_df() -> pd.DataFrame:
    try:
        from data.snowflake import get_projects
        return get_projects()
    except Exception:
        return pd.DataFrame()


def _get_dataset_ccrids() -> set[str]:
    try:
        from data.snowflake import get_demand_weight
        return set(get_demand_weight()["CCRID"].unique())
    except Exception:
        return set()


# ── Layout ────────────────────────────────────────────────────────────

layout = dbc.Container(
    [
        dcc.Location(id="inputs-nav", refresh=True),
        html.H1("Scenario Inputs"),
        dbc.Tabs(
            [
                # ═════════════════════════════════════════════════════
                # TAB 1: Scenario Parameters
                # ═════════════════════════════════════════════════════
                dbc.Tab(
                    label="Scenario Parameters",
                    tab_id="tab-params",
                    children=dbc.Container(
                        [
                            # Top row: name + regions
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Scenario name"),
                                            dbc.Input(
                                                id="input-scenario-name",
                                                type="text",
                                                value="Scenario 1",
                                            ),
                                        ],
                                        md=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Regions"),
                                            dcc.Dropdown(
                                                id="input-regions",
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
                                            section_header("Date Range"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Start date"),
                                                            dcc.DatePickerSingle(
                                                                id="input-start-date",
                                                                date=DEFAULT_START_DATE.isoformat(),
                                                                display_format="MM/DD/YYYY",
                                                                className="w-100",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("End date"),
                                                            dcc.DatePickerSingle(
                                                                id="input-end-date",
                                                                date=DEFAULT_END_DATE.isoformat(),
                                                                display_format="MM/DD/YYYY",
                                                                className="w-100",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            section_header("Workforce Assumptions"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Non-project (%)"),
                                                            dbc.Input(
                                                                id="input-pct-decrease",
                                                                type="number",
                                                                min=0,
                                                                max=100,
                                                                step=1,
                                                                value=int(DEFAULT_PCT_DECREASE * 100),
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Vacation days / year"),
                                                            dbc.Input(
                                                                id="input-vac-days",
                                                                type="number",
                                                                min=0,
                                                                max=365,
                                                                step=1,
                                                                value=DEFAULT_VAC_DAYS_PER_YEAR,
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Sick days / year"),
                                                            dbc.Input(
                                                                id="input-sick-days",
                                                                type="number",
                                                                min=0,
                                                                max=365,
                                                                step=1,
                                                                value=DEFAULT_SICK_DAYS_PER_YEAR,
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            section_header("SWAT Allocation"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("SWAT Headcount"),
                                                            dbc.Input(
                                                                id="input-swat",
                                                                type="number",
                                                                min=0,
                                                                step=1,
                                                                value=SWAT,
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            section_header("Backlog Assumptions"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Hours / CM item"),
                                                            dbc.Input(
                                                                id="input-cm-hours",
                                                                type="number",
                                                                min=0,
                                                                max=30,
                                                                step=1,
                                                                value=DEFAULT_CM_HOURS,
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Hours / PM item"),
                                                            dbc.Input(
                                                                id="input-pm-hours",
                                                                type="number",
                                                                min=0,
                                                                max=30,
                                                                step=1,
                                                                value=DEFAULT_PM_HOURS,
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
                                    # Right column: headcount adjustments
                                    dbc.Col(
                                        [
                                            section_header("Headcount Adjustments"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Adjustment start date"),
                                                            dcc.DatePickerSingle(
                                                                id="input-adj-start",
                                                                date=DEFAULT_START_DATE.isoformat(),
                                                                display_format="MM/DD/YYYY",
                                                                className="w-100",
                                                            ),
                                                        ],
                                                        md=12,
                                                        className="mb-3",
                                                    ),
                                                ],
                                            ),
                                            html.Div(id="adjustments-container"),
                                        ],
                                        md=6,
                                    ),
                                ],
                            ),
                            # Action buttons
                            dbc.Row(
                                [
                                    dbc.Col(width=3),
                                    dbc.Col(
                                        dbc.Button(
                                            "Save & Continue",
                                            id="btn-save-inputs",
                                            className="btn-ccr-primary w-100",
                                        ),
                                        md=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Run Scenario",
                                            id="btn-run-scenario",
                                            color="primary",
                                            className="w-100",
                                        ),
                                        md=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Reset Inputs",
                                            id="btn-reset-inputs",
                                            outline=True,
                                            color="secondary",
                                            className="w-100",
                                        ),
                                        md=3,
                                    ),
                                ],
                                className="mt-4 mb-4",
                            ),
                            # Validation feedback
                            html.Div(id="save-feedback"),
                            # Backlog preview
                            dbc.Accordion(
                                [
                                    dbc.AccordionItem(
                                        html.Div(id="backlog-preview-content"),
                                        title="Backlog Preview",
                                    ),
                                ],
                                start_collapsed=True,
                                className="mt-3",
                            ),
                        ],
                        fluid=True,
                        className="py-3",
                    ),
                ),
                # ═════════════════════════════════════════════════════
                # TAB 2: Projects
                # ═════════════════════════════════════════════════════
                dbc.Tab(
                    label="Projects",
                    tab_id="tab-projects",
                    children=dbc.Container(
                        [
                            section_header(
                                "Manage Projects",
                                "Exclude existing projects or add custom ones",
                            ),
                            # Remove projects section
                            section_header(
                                "Remove Projects",
                                "Excluded projects are removed from demand and supply allocation",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Filter by Region"),
                                            dcc.Dropdown(
                                                id="excl-filter-region",
                                                multi=True,
                                                placeholder="All selected regions",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Filter by Customer"),
                                            dcc.Dropdown(
                                                id="excl-filter-customer",
                                                multi=True,
                                                placeholder="All customers",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Filter by State"),
                                            dcc.Dropdown(
                                                id="excl-filter-state",
                                                multi=True,
                                                placeholder="All states",
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
                                        [
                                            dbc.Label("Projects"),
                                            dcc.Dropdown(
                                                id="excl-project-select",
                                                multi=True,
                                                placeholder="Select projects to exclude",
                                            ),
                                        ],
                                        md=8,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Exclude From"),
                                            dcc.DatePickerSingle(
                                                id="excl-date",
                                                date=DEFAULT_START_DATE.isoformat(),
                                                display_format="MM/DD/YYYY",
                                                className="w-100",
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
                                        dbc.Button(
                                            "Add Exclusion(s)",
                                            id="btn-add-exclusion",
                                            color="primary",
                                            size="sm",
                                        ),
                                        md=6,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Clear All Exclusions",
                                            id="btn-clear-exclusions",
                                            outline=True,
                                            color="danger",
                                            size="sm",
                                        ),
                                        md=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(id="excluded-projects-table"),
                            html.Hr(),
                            # Add custom projects section
                            section_header(
                                "Add Projects",
                                "Add hypothetical demand-only projects. Hours are spread evenly across scenario months.",
                            ),
                            dbc.RadioItems(
                                id="add-method",
                                options=[
                                    {"label": "Manual Entry", "value": "manual"},
                                    {"label": "CSV Upload", "value": "csv"},
                                ],
                                value="manual",
                                inline=True,
                                className="mb-3",
                            ),
                            html.Div(id="add-project-form"),
                            html.Div(id="custom-projects-table", className="mt-3"),
                        ],
                        fluid=True,
                        className="py-3",
                    ),
                ),
            ],
            id="input-tabs",
            active_tab="tab-params",
        ),
    ],
    fluid=True,
    className="py-4",
)


# ── Callbacks ────────────────────────────────────────────────────────


@callback(
    Output("input-regions", "options"),
    Input("input-regions", "id"),
)
def load_regions(_):
    regions = _get_regions()
    return [{"label": r, "value": r} for r in regions]


@callback(
    Output("input-regions", "value"),
    Output("input-scenario-name", "value"),
    Output("input-start-date", "date"),
    Output("input-end-date", "date"),
    Output("input-pct-decrease", "value"),
    Output("input-vac-days", "value"),
    Output("input-sick-days", "value"),
    Output("input-cm-hours", "value"),
    Output("input-pm-hours", "value"),
    Output("input-swat", "value"),
    Output("input-adj-start", "date"),
    Input("scenario-store", "data"),
    prevent_initial_call=True,
)
def populate_from_store(store_data):
    """Pre-fill form fields from saved store data."""
    if not store_data or not store_data.get("inputs_saved"):
        return (no_update,) * 11

    s = store_data.get("scenario", {})
    return (
        store_data.get("selected_regions", []),
        s.get("scenario_name", "Scenario 1"),
        s.get("start_date", DEFAULT_START_DATE.isoformat()),
        s.get("end_date", DEFAULT_END_DATE.isoformat()),
        int(s.get("pct_decrease", DEFAULT_PCT_DECREASE) * 100),
        int(round(s.get("vac_days_per_month", DEFAULT_VAC_DAYS_PER_YEAR / 12) * 12)),
        int(round(s.get("sick_days_per_month", DEFAULT_SICK_DAYS_PER_YEAR / 12) * 12)),
        int(s.get("cm_assumption", DEFAULT_CM_HOURS)),
        int(s.get("pm_assumption", DEFAULT_PM_HOURS)),
        int(s.get("swat_allocation", SWAT)),
        store_data.get("adjustment_start_date", DEFAULT_START_DATE.isoformat()),
    )


@callback(
    Output("adjustments-container", "children"),
    Input("input-regions", "value"),
    State("scenario-store", "data"),
)
def render_adjustments(selected_regions, store_data):
    if not selected_regions:
        return html.P(
            "Select at least one region above to configure adjustments.",
            className="text-muted",
        )

    saved_adj = {}
    if store_data and store_data.get("adjustments"):
        saved_adj = store_data["adjustments"]

    rows = []
    for i in range(0, len(selected_regions), 3):
        cols = []
        for j in range(3):
            idx = i + j
            if idx >= len(selected_regions):
                cols.append(dbc.Col(width=4))
                continue
            region = selected_regions[idx]
            cols.append(
                dbc.Col(
                    [
                        dbc.Label(region, size="sm"),
                        dbc.Input(
                            id={"type": "adj-input", "region": region},
                            type="number",
                            min=-100,
                            step=1,
                            value=int(saved_adj.get(region, 0)),
                            size="sm",
                        ),
                    ],
                    md=4,
                    className="mb-2",
                )
            )
        rows.append(dbc.Row(cols))

    return html.Div(rows)


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Output("save-feedback", "children"),
    Output("inputs-nav", "href"),
    Input("btn-save-inputs", "n_clicks"),
    Input("btn-run-scenario", "n_clicks"),
    Input("btn-reset-inputs", "n_clicks"),
    State("input-scenario-name", "value"),
    State("input-regions", "value"),
    State("input-start-date", "date"),
    State("input-end-date", "date"),
    State("input-pct-decrease", "value"),
    State("input-vac-days", "value"),
    State("input-sick-days", "value"),
    State("input-cm-hours", "value"),
    State("input-pm-hours", "value"),
    State("input-swat", "value"),
    State("input-adj-start", "date"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def save_or_reset(
    n_save, n_run, n_reset,
    name, regions, start, end, pct, vac, sick, cm, pm, swat, adj_start,
    store_data,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "btn-reset-inputs":
        return None, dbc.Alert("Inputs reset.", color="info", duration=3000), no_update

    # Validate
    errors = []
    if start and end and start > end:
        errors.append("Start date must be before end date.")
    if not regions:
        errors.append("Select at least one region.")
    if errors:
        return no_update, html.Div([dbc.Alert(e, color="danger") for e in errors]), no_update

    # Collect adjustments from pattern-matching
    # (We read adjustments via a separate callback and merge them in)
    existing_adj = store_data.get("adjustments", {}) if store_data else {}

    new_store = {
        "inputs_saved": True,
        "scenario": {
            "scenario_name": name or "Scenario 1",
            "pct_decrease": (pct or 15) / 100,
            "vac_days_per_month": (vac or 20) / 12,
            "sick_days_per_month": (sick or 8) / 12,
            "start_date": start,
            "end_date": end,
            "pm_assumption": pm or DEFAULT_PM_HOURS,
            "cm_assumption": cm or DEFAULT_CM_HOURS,
            "swat_allocation": swat or 0,
        },
        "selected_regions": regions or [],
        "adjustments": existing_adj,
        "adjustment_start_date": adj_start,
        "excluded_projects": (store_data or {}).get("excluded_projects", []),
        "custom_projects": (store_data or {}).get("custom_projects", []),
    }

    if trigger == "btn-run-scenario":
        return new_store, dbc.Alert("Inputs saved!", color="success", duration=2000), "/results"

    return new_store, dbc.Alert("Inputs saved!", color="success", duration=3000), no_update


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Input({"type": "adj-input", "region": dash.ALL}, "value"),
    State({"type": "adj-input", "region": dash.ALL}, "id"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def sync_adjustments(values, ids, store_data):
    """Keep adjustments in store in sync with the input fields."""
    if not ids or not values:
        return no_update
    store_data = store_data or {}
    adj = {}
    for id_dict, val in zip(ids, values):
        adj[id_dict["region"]] = int(val or 0)
    store_data["adjustments"] = adj
    return store_data


# ── Project exclusion callbacks ──────────────────────────────────────


@callback(
    Output("excl-filter-region", "options"),
    Output("excl-filter-customer", "options"),
    Output("excl-filter-state", "options"),
    Output("excl-project-select", "options"),
    Input("excl-filter-region", "value"),
    Input("excl-filter-customer", "value"),
    Input("excl-filter-state", "value"),
    State("input-regions", "value"),
    State("scenario-store", "data"),
)
def update_project_filters(filt_region, filt_customer, filt_state, selected_regions, store_data):
    projects_df = _get_projects_df()
    if projects_df.empty:
        return [], [], [], []

    dataset_ccrids = _get_dataset_ccrids()
    in_dataset = projects_df[projects_df["CCRID"].isin(dataset_ccrids)].copy()

    if selected_regions:
        in_dataset = in_dataset[in_dataset["REGION"].isin(selected_regions)]

    region_opts = [{"label": r, "value": r} for r in sorted(in_dataset["REGION"].dropna().unique())]
    customer_opts = [{"label": c, "value": c} for c in sorted(in_dataset["CUSTOMER"].dropna().unique())]
    state_opts = [{"label": s, "value": s} for s in sorted(in_dataset["STATE"].dropna().unique())]

    filtered = in_dataset
    if filt_region:
        filtered = filtered[filtered["REGION"].isin(filt_region)]
    if filt_customer:
        filtered = filtered[filtered["CUSTOMER"].isin(filt_customer)]
    if filt_state:
        filtered = filtered[filtered["STATE"].isin(filt_state)]

    already_excluded = set()
    if store_data and store_data.get("excluded_projects"):
        already_excluded = {p["CCRID"] for p in store_data["excluded_projects"]}

    available = filtered[~filtered["CCRID"].isin(already_excluded)].drop_duplicates(subset="CCRID")
    project_opts = [
        {"label": f"{row.PROJECT_NAME} ({row.CCRID})", "value": row.CCRID}
        for row in available.itertuples()
    ]

    return region_opts, customer_opts, state_opts, project_opts


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Output("excluded-projects-table", "children"),
    Output("excl-project-select", "value"),
    Input("btn-add-exclusion", "n_clicks"),
    Input("btn-clear-exclusions", "n_clicks"),
    State("excl-project-select", "value"),
    State("excl-date", "date"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def manage_exclusions(n_add, n_clear, selected_ccrids, excl_date, store_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    store_data = store_data or {}
    excluded = store_data.get("excluded_projects", [])

    if trigger == "btn-clear-exclusions":
        store_data["excluded_projects"] = []
        return store_data, html.P("No projects excluded.", className="text-muted"), []

    if trigger == "btn-add-exclusion" and selected_ccrids:
        projects_df = _get_projects_df()
        name_map = dict(zip(projects_df["CCRID"], projects_df["PROJECT_NAME"]))
        for ccrid in selected_ccrids:
            excluded.append({
                "CCRID": ccrid,
                "PROJECT_NAME": name_map.get(ccrid, ccrid),
                "EXCLUDE_FROM": excl_date,
            })
        store_data["excluded_projects"] = excluded

    if excluded:
        table = dag.AgGrid(
            rowData=excluded,
            columnDefs=[
                {"field": "CCRID", "headerName": "CCRID", "width": 150},
                {"field": "PROJECT_NAME", "headerName": "Project", "flex": 1},
                {"field": "EXCLUDE_FROM", "headerName": "Exclude From", "width": 150},
            ],
            defaultColDef={"sortable": True, "filter": True, "resizable": True},
            style={"height": "250px"},
            className="ag-theme-alpine",
        )
        content = html.Div([
            section_header("Excluded Projects", f"{len(excluded)} project(s) excluded"),
            table,
        ])
    else:
        content = html.P("No projects excluded.", className="text-muted")

    return store_data, content, []


# ── Custom project callbacks ─────────────────────────────────────────


@callback(
    Output("add-project-form", "children"),
    Input("add-method", "value"),
)
def render_add_form(method):
    if method == "csv":
        return html.Div([
            html.P(
                "CSV must contain columns: CCRID, PROJECT_NAME, REGION, TOTAL_HOURS, START_DATE (YYYY-MM-DD).",
                className="text-muted small",
            ),
            dcc.Upload(
                id="csv-upload",
                children=dbc.Button("Upload CSV", outline=True, color="info", className="w-100"),
                className="mb-2",
            ),
            html.Div(id="csv-feedback"),
        ])

    regions = _get_regions()
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Label("Project Name"),
                    dbc.Input(id="new-proj-name", type="text"),
                ],
                md=3,
            ),
            dbc.Col(
                [
                    dbc.Label("Region"),
                    dcc.Dropdown(
                        id="new-proj-region",
                        options=[{"label": r, "value": r} for r in regions],
                    ),
                ],
                md=3,
            ),
            dbc.Col(
                [
                    dbc.Label("Total Hours"),
                    dbc.Input(id="new-proj-hours", type="number", min=0, step=100, value=0),
                ],
                md=2,
            ),
            dbc.Col(
                [
                    dbc.Label("Start Date"),
                    dcc.DatePickerSingle(
                        id="new-proj-start",
                        date=DEFAULT_START_DATE.isoformat(),
                        display_format="MM/DD/YYYY",
                        className="w-100",
                    ),
                ],
                md=2,
            ),
            dbc.Col(
                dbc.Button(
                    "Add Project",
                    id="btn-add-project",
                    color="primary",
                    className="w-100 mt-4",
                ),
                md=2,
            ),
        ],
        className="mb-3",
    )


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Output("custom-projects-table", "children"),
    Input("btn-add-project", "n_clicks"),
    State("new-proj-name", "value"),
    State("new-proj-region", "value"),
    State("new-proj-hours", "value"),
    State("new-proj-start", "date"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def add_custom_project(n_clicks, name, region, hours, start_date, store_data):
    if not n_clicks or not name or not name.strip():
        return no_update, no_update

    store_data = store_data or {}
    custom = store_data.get("custom_projects", [])
    counter = len(custom) + 1
    custom.append({
        "CCRID": f"CUSTOM_{counter:03d}",
        "PROJECT_NAME": name.strip(),
        "REGION": region,
        "TOTAL_HOURS": hours or 0,
        "START_DATE": start_date,
    })
    store_data["custom_projects"] = custom

    return store_data, _render_custom_table(custom)


def _render_custom_table(custom: list[dict]) -> html.Div:
    if not custom:
        return html.Div()

    return html.Div([
        section_header("Custom Projects", f"{len(custom)} project(s) added"),
        dag.AgGrid(
            rowData=custom,
            columnDefs=[
                {"field": "CCRID", "headerName": "CCRID", "width": 150},
                {"field": "PROJECT_NAME", "headerName": "Project", "flex": 1},
                {"field": "REGION", "headerName": "Region", "width": 150},
                {"field": "TOTAL_HOURS", "headerName": "Hours", "width": 100},
                {"field": "START_DATE", "headerName": "Start", "width": 130},
            ],
            defaultColDef={"sortable": True, "resizable": True},
            style={"height": "200px"},
            className="ag-theme-alpine",
        ),
        dbc.Button(
            "Clear All Custom Projects",
            id="btn-clear-custom",
            outline=True,
            color="danger",
            size="sm",
            className="mt-2",
        ),
    ])


# ── Backlog preview callback ────────────────────────────────────────


@callback(
    Output("backlog-preview-content", "children"),
    Input("input-cm-hours", "value"),
    Input("input-pm-hours", "value"),
)
def update_backlog_preview(cm_hours, pm_hours):
    cm_hours = cm_hours or DEFAULT_CM_HOURS
    pm_hours = pm_hours or DEFAULT_PM_HOURS

    try:
        from data.snowflake import get_backlog, get_cm_backlog, get_pm_backlog
        from components.charts import backlog_by_region_chart, pm_vs_cm_chart

        backlog_df = get_backlog(pm_hours, cm_hours)
        if backlog_df.empty:
            return html.P("No backlog data available.", className="text-muted")

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

        # Metrics row
        metrics = dbc.Row([
            dbc.Col(html.Div([html.Small("Total Jobs"), html.H5(f"{total_items:,}")], className="kpi-card"), md=2),
            dbc.Col(html.Div([html.Small("Total Hours"), html.H5(f"{total_hours:,.0f}")], className="kpi-card"), md=2),
            dbc.Col(html.Div([html.Small("PM Jobs"), html.H5(f"{pm_items:,}")], className="kpi-card"), md=2),
            dbc.Col(html.Div([html.Small("CM Jobs"), html.H5(f"{cm_items:,}")], className="kpi-card"), md=2),
            dbc.Col(html.Div([html.Small("Regions"), html.H5(f"{n_regions}")], className="kpi-card"), md=2),
            dbc.Col(html.Div([html.Small("Projects"), html.H5(f"{n_projects}")], className="kpi-card"), md=2),
        ], className="mb-3 g-2")

        # Charts
        by_region = (
            backlog_df.groupby("REGION", as_index=False)
            .agg(ITEMS=("COUNT", "sum"), HOURS=("HOURS", "sum"))
            .sort_values("HOURS", ascending=True)
        )

        pm_by_region = pm_df.groupby("REGION", as_index=False)["COUNT"].sum().rename(columns={"COUNT": "PM"})
        cm_by_region = cm_df.groupby("REGION", as_index=False)["COUNT"].sum().rename(columns={"COUNT": "CM"})
        breakdown = pm_by_region.merge(cm_by_region, on="REGION", how="outer").fillna(0)
        breakdown["PM_HRS"] = breakdown["PM"] * pm_hours
        breakdown["CM_HRS"] = breakdown["CM"] * cm_hours

        charts = dbc.Row([
            dbc.Col(dcc.Graph(figure=backlog_by_region_chart(by_region), config={"displayModeBar": False}), md=6),
            dbc.Col(dcc.Graph(figure=pm_vs_cm_chart(breakdown), config={"displayModeBar": False}), md=6),
        ])

        return html.Div([metrics, charts])

    except Exception as exc:
        return dbc.Alert(f"Could not load backlog data: {exc}", color="warning")
