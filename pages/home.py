"""Home page — system status and quick navigation."""

import dash
import dash_bootstrap_components as dbc
from dash import callback, dcc, html, Input, Output, State, no_update

from components.branding import LIGHT_BLUE, NAVY, section_header, status_badge
from config import build_demo_preset

dash.register_page(__name__, path="/", name="Home", order=0)

# ── Layout ────────────────────────────────────────────────────────────

layout = dbc.Container(
    [
        # Local redirect component
        dcc.Location(id="home-nav", refresh=True),
        # Hero banner
        html.Div(
            [
                html.H1("Staffing Supply & Demand"),
                html.P(
                    "Model workforce capacity against project demand. Configure scenarios, "
                    "adjust headcount, and analyse supply gaps across regions."
                ),
            ],
            className="hero-banner",
        ),
        # Connection status
        html.Div(id="home-connection-status", className="mb-3"),
        # Quick actions — use dcc.Link for simple nav, button+callback for demo
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Link(
                            dbc.Button(
                                "Configure Inputs",
                                className="btn-ccr-primary w-100 mb-2",
                            ),
                            href="/inputs",
                        ),
                        html.P(
                            "Set scenario parameters, regions, and headcount adjustments.",
                            className="text-muted small",
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        dbc.Button(
                            "Load Demo & Run",
                            id="btn-demo",
                            color="primary",
                            className="w-100 mb-2",
                        ),
                        html.P(
                            "Run a pre-configured demo scenario with randomised inputs.",
                            className="text-muted small",
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        dcc.Link(
                            dbc.Button(
                                "View Results",
                                outline=True,
                                color="secondary",
                                className="w-100 mb-2",
                            ),
                            href="/results",
                        ),
                        html.P(
                            "Analyse KPIs, charts, and backlog trends.",
                            className="text-muted small",
                        ),
                    ],
                    md=4,
                ),
            ],
            className="mb-4",
        ),
        # System diagnostics
        dbc.Accordion(
            [
                dbc.AccordionItem(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Button(
                                        "Test Connection",
                                        id="btn-test-conn",
                                        outline=True,
                                        color="info",
                                        size="sm",
                                        className="w-100",
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Load Regions",
                                        id="btn-load-regions",
                                        outline=True,
                                        color="info",
                                        size="sm",
                                        className="w-100",
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Reset Connection",
                                        id="btn-reset-conn",
                                        outline=True,
                                        color="warning",
                                        size="sm",
                                        className="w-100",
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Clear Data Cache",
                                        id="btn-clear-cache",
                                        outline=True,
                                        color="warning",
                                        size="sm",
                                        className="w-100",
                                    ),
                                    md=3,
                                ),
                            ],
                            className="mb-3",
                        ),
                        html.Div(id="diag-output"),
                    ],
                    title="System Diagnostics",
                ),
            ],
            start_collapsed=True,
        ),
    ],
    fluid=True,
    className="py-4",
)

# ── Callbacks ────────────────────────────────────────────────────────


@callback(
    Output("home-connection-status", "children"),
    Input("home-connection-status", "id"),  # fires on page load
)
def check_connection_on_load(_):
    try:
        from data.snowflake import get_regions_df
        regions_df = get_regions_df()
        if not regions_df.empty:
            return status_badge(f"Connected — {len(regions_df)} regions loaded")
        return dbc.Alert("Connected, but no regions returned.", color="warning")
    except Exception as exc:
        return dbc.Alert(f"Snowflake connection failed: {exc}", color="danger")


@callback(
    Output("home-nav", "href"),
    Output("scenario-store", "data", allow_duplicate=True),
    Input("btn-demo", "n_clicks"),
    State("scenario-store", "data"),
    prevent_initial_call=True,
)
def load_demo(n_demo, store_data):
    if not n_demo:
        return no_update, no_update

    preset = build_demo_preset()
    demo_store = {
        "inputs_saved": True,
        "scenario": {
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in preset["scenario"].items()
        },
        "selected_regions": preset["selected_regions"],
        "adjustments": preset["adjustments"],
        "adjustment_start_date": preset["adjustment_start_date"].isoformat(),
        "excluded_projects": preset["excluded_projects"],
        "custom_projects": preset["custom_projects"],
    }
    return "/results", demo_store


@callback(
    Output("diag-output", "children"),
    Input("btn-test-conn", "n_clicks"),
    Input("btn-load-regions", "n_clicks"),
    Input("btn-reset-conn", "n_clicks"),
    Input("btn-clear-cache", "n_clicks"),
    prevent_initial_call=True,
)
def run_diagnostics(n_test, n_regions, n_reset, n_clear):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        from data.snowflake import (
            clear_data_cache,
            get_connection_info,
            get_regions_df,
            reset_connection,
        )

        if trigger == "btn-test-conn":
            info = get_connection_info()
            return dbc.Table.from_dataframe(info, striped=True, bordered=True, size="sm")

        elif trigger == "btn-load-regions":
            regions_df = get_regions_df()
            if regions_df.empty:
                return dbc.Alert("No regions returned.", color="warning")
            return html.Div([
                status_badge(f"{len(regions_df)} regions loaded"),
                dbc.Table.from_dataframe(regions_df, striped=True, bordered=True, size="sm", className="mt-2"),
            ])

        elif trigger == "btn-reset-conn":
            reset_connection()
            return status_badge("Connection reset", LIGHT_BLUE)

        elif trigger == "btn-clear-cache":
            clear_data_cache()
            return status_badge("Data cache cleared", LIGHT_BLUE)

    except Exception as exc:
        return dbc.Alert(f"Error: {exc}", color="danger")

    return no_update
