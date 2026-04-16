"""Dash application entry point — Supply & Demand workforce planner."""

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dotenv import load_dotenv

# Load environment variables from .env (Snowflake credentials, etc.)
load_dotenv()

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Supply & Demand | CCR",
    update_title="Loading...",
)
server = app.server

# ── Navigation bar ────────────────────────────────────────────────────

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.jpg"

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            src=app.get_asset_url("logo.jpg"),
                            height="36px",
                            className="me-2",
                        )
                        if _LOGO_PATH.exists()
                        else html.Span(
                            "CCR",
                            className="fw-bold text-white fs-5",
                        ),
                    ),
                    dbc.Col(
                        dbc.NavbarBrand(
                            "Supply & Demand",
                            className="fw-bold",
                        ),
                    ),
                ],
                align="center",
                className="g-0",
            ),
            dbc.Nav(
                [
                    dbc.NavItem(
                        dbc.NavLink(
                            page["name"],
                            href=page["path"],
                            active="exact",
                            className="nav-link-custom",
                        )
                    )
                    for page in dash.page_registry.values()
                ],
                className="ms-auto",
                navbar=True,
            ),
        ],
        fluid=True,
    ),
    color="#072d68",
    dark=True,
    className="mb-0",
    style={"borderBottom": "3px solid #008bc1"},
)

# ── Layout ────────────────────────────────────────────────────────────

app.layout = html.Div(
    [
        dcc.Store(id="scenario-store", storage_type="session"),
        navbar,
        html.Div(dash.page_container, className="page-container"),
    ]
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
