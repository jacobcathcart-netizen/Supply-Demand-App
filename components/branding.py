"""CCR corporate branding — colors, fonts, and custom CSS."""

from __future__ import annotations

import streamlit as st

# ── CCR Brand Colors ─────────────────────────────────────────────────
NAVY = "#0A3370"
BLUE = "#2C31A6"
LIGHT_BLUE = "#1892DF"
TEAL = "#33CCA6"
GREEN = "#007647"
ORANGE = "#F26419"
GOLD = "#F9A620"

# Chart palette (ordered for visual clarity)
CHART_COLORS = [LIGHT_BLUE, NAVY, TEAL, ORANGE, GOLD, GREEN, BLUE]

# Table alternating row color (15% black ≈ #D9D9D9)
TABLE_ALT_ROW = "#D9D9D9"

# ── Custom CSS ───────────────────────────────────────────────────────

_CUSTOM_CSS = """
<style>
/* Force Tahoma across the app */
html, body, [class*="css"] {
    font-family: Tahoma, Geneva, Verdana, sans-serif;
}

/* Metric labels */
[data-testid="stMetricLabel"] {
    font-family: Tahoma, Geneva, Verdana, sans-serif;
    color: %(navy)s;
}

/* Metric values */
[data-testid="stMetricValue"] {
    font-family: Tahoma, Geneva, Verdana, sans-serif;
    color: %(navy)s;
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    font-family: Tahoma, Geneva, Verdana, sans-serif;
    color: %(navy)s;
}

/* Dataframe tables — no borders, alternating rows */
[data-testid="stDataFrame"] table {
    border-collapse: collapse;
}
[data-testid="stDataFrame"] th {
    background: linear-gradient(180deg, %(light_blue)s 0%%, %(navy)s 100%%);
    color: white;
    font-family: Tahoma, Geneva, Verdana, sans-serif;
    font-weight: bold;
    border: none;
    padding: 8px 12px;
}
[data-testid="stDataFrame"] td {
    border: none;
    padding: 6px 12px;
    font-family: Tahoma, Geneva, Verdana, sans-serif;
}
[data-testid="stDataFrame"] tr:nth-child(even) td {
    background-color: %(alt_row)s;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: %(navy)s;
}
[data-testid="stSidebar"] * {
    color: white;
}

/* Primary button styling */
.stButton > button[kind="primary"] {
    background-color: %(light_blue)s;
    border-color: %(light_blue)s;
    font-family: Tahoma, Geneva, Verdana, sans-serif;
}

/* Container borders in brand color */
[data-testid="stContainer"] {
    border-color: %(light_blue)s !important;
}
</style>
""" % {
    "navy": NAVY,
    "light_blue": LIGHT_BLUE,
    "alt_row": TABLE_ALT_ROW,
}


def apply_branding() -> None:
    """Inject CCR custom CSS into the current page."""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
