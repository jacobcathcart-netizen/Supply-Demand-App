"""CCR corporate branding — colors, constants, and Dash helper components."""

from __future__ import annotations

from dash import html
import dash_bootstrap_components as dbc

# ── CCR Brand Colors (official) ──────────────────────────────────────
NAVY = "#072d68"            # CCR Blue — primary
LIGHT_BLUE = "#008bc1"      # CCR Light Blue — secondary / accents / actions
YELLOW = "#f5ac1c"          # CCR Yellow — accent, CTAs, hover highlights
LIGHT_GRAY = "#ebebeb"      # CCR Light Gray — backgrounds, dividers
GRAY = "#333333"            # CCR Gray — body text

# Chart-specific colors (kept for data differentiation)
BLUE = "#2C31A6"
TEAL = "#33CCA6"
ORANGE = "#F26419"
GOLD = "#F9A620"
GREEN = "#007647"

# Warm neutrals
WHITE = "#FFFFFF"
WARM_WHITE = "#E6E5E5"      # Page background — barely warm
GRAY_200 = "#D9DDE5"        # Borders
DARK = "#0a2550"            # Sidebar bottom (darker CCR Blue shade)

# Backward-compat aliases
GRAY_50 = LIGHT_GRAY
GRAY_100 = LIGHT_GRAY
GRAY_600 = GRAY

# Chart palette (ordered for visual clarity)
CHART_COLORS = [LIGHT_BLUE, NAVY, TEAL, ORANGE, GOLD, GREEN, BLUE]

# Table alternating row color
TABLE_ALT_ROW = "#D9D9D9"


# ── Dash helper components ──────────────────────────────────────────


def section_header(title: str, subtitle: str | None = None) -> html.Div:
    """Return a styled section header with optional subtitle."""
    children = [
        html.H5(
            title,
            style={
                "color": NAVY,
                "fontWeight": "600",
                "fontFamily": "Tahoma, Geneva, sans-serif",
                "marginBottom": "0.25rem",
                "borderBottom": f"2px solid {LIGHT_BLUE}",
                "paddingBottom": "0.25rem",
            },
        )
    ]
    if subtitle:
        children.append(
            html.P(
                subtitle,
                className="text-muted small mb-2",
                style={"fontFamily": "Tahoma, Geneva, sans-serif"},
            )
        )
    return html.Div(children, className="mb-3")


def status_badge(text: str, color: str = LIGHT_BLUE) -> dbc.Badge:
    """Return a styled status badge."""
    return dbc.Badge(
        text,
        color="",
        style={
            "border": f"1.5px solid {color}",
            "color": color,
            "background": "transparent",
            "padding": "0.15rem 0.65rem",
            "borderRadius": "4px",
            "fontSize": "0.72rem",
            "fontWeight": "700",
            "fontFamily": "Tahoma, Geneva, sans-serif",
            "letterSpacing": "0.03em",
        },
    )
