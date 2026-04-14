"""Top navigation bar with CCR branding."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

# ── CCR Colors ──────────────────────────────────────────────────────
NAVY = "#0a3370"
LIGHT_BLUE = "#008bc1"

navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.A(
                            html.Img(
                                src="/assets/logo.jpg",
                                height="36px",
                                style={"borderRadius": "4px"},
                            ),
                            href="/",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Span(
                            "Workforce Planning",
                            style={
                                "color": "rgba(255,255,255,0.85)",
                                "fontSize": "0.8rem",
                                "fontFamily": "Tahoma, Geneva, sans-serif",
                                "marginLeft": "0.5rem",
                            },
                        ),
                        width="auto",
                        className="d-none d-md-block",
                    ),
                ],
                align="center",
                className="g-2",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Home", href="/", className="nav-link-custom")),
                        dbc.NavItem(dbc.NavLink("Inputs", href="/inputs", className="nav-link-custom")),
                        dbc.NavItem(dbc.NavLink("Results", href="/results", className="nav-link-custom")),
                    ],
                    navbar=True,
                    className="ms-auto",
                ),
                id="navbar-collapse",
                navbar=True,
            ),
        ],
        fluid=True,
    ),
    color=NAVY,
    dark=True,
    style={
        "background": f"linear-gradient(135deg, {NAVY} 0%, #0a2550 100%)",
        "fontFamily": "Tahoma, Geneva, sans-serif",
        "boxShadow": "0 2px 8px rgba(10,51,112,0.25)",
        "padding": "0.5rem 0",
    },
    className="mb-0",
)
