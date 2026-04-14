"""Home page — system status and quick navigation."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

dash.register_page(__name__, path="/", name="Home")

# ── Layout ─────────────────────────────────────────────────────────

layout = html.Div(
    [
        # Hero banner
        html.Div(
            [
                html.H1("Staffing Supply & Demand"),
                html.P(
                    "Model workforce capacity against project demand. Configure "
                    "scenarios, adjust headcount, and analyse supply gaps across regions."
                ),
            ],
            className="hero-banner",
        ),
        # Connection status
        html.Div(id="home-connection-status", className="mb-3"),
        # Quick actions
        dbc.Row(
            [
                dbc.Col(
                    dcc.Link(
                        html.Div(
                            [
                                html.H3("Configure Inputs"),
                                html.P("Set scenario parameters, regions, and headcount adjustments."),
                            ],
                            className="action-card",
                        ),
                        href="/inputs",
                        style={"textDecoration": "none"},
                    ),
                    md=4,
                    className="mb-3",
                ),
                dbc.Col(
                    html.Div(
                        [
                            html.H3("Load Demo & Run"),
                            html.P("Run a pre-configured demo scenario with randomised inputs."),
                        ],
                        id="demo-card",
                        className="action-card",
                        style={"border": "2px solid #008bc1"},
                    ),
                    md=4,
                    className="mb-3",
                ),
                dbc.Col(
                    dcc.Link(
                        html.Div(
                            [
                                html.H3("View Results"),
                                html.P("Analyse KPIs, charts, and backlog trends."),
                            ],
                            className="action-card",
                        ),
                        href="/results",
                        style={"textDecoration": "none"},
                    ),
                    md=4,
                    className="mb-3",
                ),
            ],
            className="mb-4",
        ),
        # System diagnostics
        html.Details(
            [
                html.Summary(
                    "System Diagnostics",
                    style={
                        "fontWeight": "600",
                        "color": "#0a3370",
                        "cursor": "pointer",
                        "padding": "0.75rem 0",
                    },
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Button(
                                "Test Connection",
                                id="btn-test-conn",
                                className="btn-ccr-secondary",
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            html.Button(
                                "Load Regions",
                                id="btn-load-regions",
                                className="btn-ccr-secondary",
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            html.Button(
                                "Reset Connection",
                                id="btn-reset-conn",
                                className="btn-ccr-secondary",
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            html.Button(
                                "Clear Data Cache",
                                id="btn-clear-cache",
                                className="btn-ccr-secondary",
                            ),
                            md=3,
                        ),
                    ],
                    className="g-2 mb-3",
                ),
                html.Div(id="diagnostics-output"),
            ],
            className="mb-4",
        ),
    ]
)

# ── Callbacks ──────────────────────────────────────────────────────


@callback(
    Output("home-connection-status", "children"),
    Input("url", "pathname"),
)
def auto_connect(pathname):
    """Auto-connect to Snowflake when the Home page loads."""
    if pathname != "/":
        return dash.no_update
    try:
        from data_adapter import get_regions_df

        regions_df = get_regions_df()
        if not regions_df.empty:
            return html.Span(
                f"Connected — {len(regions_df)} regions loaded",
                className="status-badge",
            )
        return html.Span(
            "Connected, but no regions returned.",
            className="status-badge",
            style={"borderColor": "#f5ac1c", "color": "#f5ac1c"},
        )
    except Exception as exc:
        return html.Div(
            f"Snowflake connection failed: {exc}",
            className="alert-info-ccr",
            style={"borderColor": "#dc3545", "color": "#dc3545"},
        )


@callback(
    Output("scenario-store", "data", allow_duplicate=True),
    Output("projects-store", "data", allow_duplicate=True),
    Output("url", "pathname", allow_duplicate=True),
    Input("demo-card", "n_clicks"),
    prevent_initial_call=True,
)
def load_demo(n_clicks):
    """Load demo preset and navigate to Results."""
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update

    from config import build_demo_preset

    preset = build_demo_preset()
    scenario_data = {
        "inputs_saved": True,
        "scenario": {
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in preset["scenario"].items()
        },
        "selected_regions": preset["selected_regions"],
        "adjustments": preset["adjustments"],
        "adjustment_start_date": preset["adjustment_start_date"].isoformat(),
    }
    projects_data = {
        "excluded_projects": preset["excluded_projects"],
        "custom_projects": preset["custom_projects"],
    }
    return scenario_data, projects_data, "/results"


@callback(
    Output("diagnostics-output", "children"),
    Input("btn-test-conn", "n_clicks"),
    Input("btn-load-regions", "n_clicks"),
    Input("btn-reset-conn", "n_clicks"),
    Input("btn-clear-cache", "n_clicks"),
    prevent_initial_call=True,
)
def diagnostics(test_clicks, load_clicks, reset_clicks, clear_clicks):
    """Handle diagnostic button clicks."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        from data_adapter import get_connection_info, get_regions_df, reset_connection

        if btn_id == "btn-test-conn":
            info = get_connection_info()
            return html.Div(
                [
                    dash_table.DataTable(
                        data=info.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in info.columns],
                        style_header={
                            "backgroundColor": "#0a3370",
                            "color": "white",
                            "fontWeight": "600",
                        },
                        style_cell={"fontFamily": "Tahoma", "fontSize": "0.85rem"},
                    ),
                    html.Span("Connected", className="status-badge mt-2"),
                ]
            )

        if btn_id == "btn-load-regions":
            regions_df = get_regions_df()
            if regions_df.empty:
                return html.Div("No regions returned.", className="alert-info-ccr")
            return html.Div(
                [
                    dash_table.DataTable(
                        data=regions_df.to_dict("records"),
                        columns=[{"name": c, "id": c} for c in regions_df.columns],
                        style_header={
                            "backgroundColor": "#0a3370",
                            "color": "white",
                            "fontWeight": "600",
                        },
                        style_cell={"fontFamily": "Tahoma", "fontSize": "0.85rem"},
                    ),
                    html.Span(
                        f"{len(regions_df)} regions loaded",
                        className="status-badge mt-2",
                    ),
                ]
            )

        if btn_id == "btn-reset-conn":
            reset_connection()
            return html.Span("Connection reset", className="status-badge")

        if btn_id == "btn-clear-cache":
            from data_adapter import _cache_clear
            _cache_clear()
            return html.Span("Data cache cleared", className="status-badge")

    except Exception as exc:
        return html.Div(f"Error: {exc}", className="alert-info-ccr")

    return dash.no_update
