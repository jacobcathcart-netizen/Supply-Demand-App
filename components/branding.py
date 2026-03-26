"""CCR corporate branding — colors, fonts, and enterprise CSS."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# ── Asset paths ──────────────────────────────────────────────────────
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_LOGO_PATH = _ASSETS_DIR / "logo.jpg"
HERO_IMAGE_PATH = _ASSETS_DIR / "solar_farm.jpg"

# ── CCR Brand Colors ─────────────────────────────────────────────────
NAVY = "#0A3370"
BLUE = "#2C31A6"
LIGHT_BLUE = "#1892DF"
TEAL = "#33CCA6"
GREEN = "#007647"
ORANGE = "#F26419"
GOLD = "#F9A620"

# Neutrals
WHITE = "#FFFFFF"
GRAY_50 = "#F8F9FC"
GRAY_100 = "#EEF1F6"
GRAY_200 = "#D9DDE5"
GRAY_600 = "#5A6378"
DARK = "#1A1F2E"

# Chart palette (ordered for visual clarity)
CHART_COLORS = [LIGHT_BLUE, NAVY, TEAL, ORANGE, GOLD, GREEN, BLUE]

# Table alternating row color (15% black ≈ #D9D9D9)
TABLE_ALT_ROW = "#D9D9D9"

# ── Custom CSS ───────────────────────────────────────────────────────

_CUSTOM_CSS = f"""
<style>
/* ─── Global font ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: Tahoma, 'Inter', Geneva, Verdana, sans-serif;
}}

/* ─── Hide Streamlit default chrome ───────────────────────────── */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* ─── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {NAVY} 0%, {DARK} 100%);
    border-right: none;
    padding-top: 1.5rem;
}}
[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
}}
[data-testid="stSidebar"] .stRadio label:hover,
[data-testid="stSidebar"] a:hover {{
    color: {TEAL} !important;
}}
[data-testid="stSidebarNavItems"] {{
    padding-top: 1rem;
}}
[data-testid="stSidebarNavLink"] {{
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin: 0.15rem 0.5rem;
    transition: background 0.2s ease;
}}
[data-testid="stSidebarNavLink"]:hover {{
    background: rgba(255,255,255,0.08);
}}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: rgba(24,146,223,0.2);
    border-left: 3px solid {LIGHT_BLUE};
}}

/* ─── Page header area ────────────────────────────────────────── */
h1 {{
    font-family: Tahoma, 'Inter', sans-serif;
    color: {NAVY};
    font-weight: 700;
    letter-spacing: -0.02em;
    padding-bottom: 0.25rem;
    border-bottom: 3px solid {LIGHT_BLUE};
    margin-bottom: 1.5rem;
}}
h2, h3 {{
    font-family: Tahoma, 'Inter', sans-serif;
    color: {NAVY};
    font-weight: 600;
}}
h4, h5, h6 {{
    font-family: Tahoma, 'Inter', sans-serif;
    color: {GRAY_600};
    font-weight: 600;
}}

/* ─── Metric cards ────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {WHITE};
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(10,51,112,0.06);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: 0 4px 12px rgba(10,51,112,0.12);
    transform: translateY(-1px);
}}
[data-testid="stMetricLabel"] {{
    font-family: Tahoma, 'Inter', sans-serif;
    color: {GRAY_600};
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] {{
    font-family: Tahoma, 'Inter', sans-serif;
    color: {NAVY};
    font-weight: 700;
}}
[data-testid="stMetricDelta"] svg {{
    display: inline;
}}

/* ─── Containers / cards ──────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: {WHITE};
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(10,51,112,0.06);
    margin-bottom: 1rem;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 600;
    color: {NAVY};
    padding: 0.75rem 1rem;
}}
[data-testid="stExpander"] summary:hover {{
    background: {GRAY_50};
}}

/* Bordered containers */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
    border: 1px solid {GRAY_200} !important;
    border-radius: 12px !important;
    background: {WHITE};
    box-shadow: 0 1px 3px rgba(10,51,112,0.06);
    padding: 0.5rem;
}}

/* ─── Buttons ─────────────────────────────────────────────────── */
.stButton > button {{
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s ease;
    border: 1px solid {GRAY_200};
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"] {{
    background: linear-gradient(135deg, {LIGHT_BLUE} 0%, {BLUE} 100%);
    color: {WHITE};
    border: none;
    box-shadow: 0 2px 8px rgba(24,146,223,0.3);
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px rgba(24,146,223,0.4);
    transform: translateY(-1px);
}}
.stButton > button[kind="secondary"]:hover {{
    border-color: {LIGHT_BLUE};
    color: {LIGHT_BLUE};
}}

/* ─── Form styling ────────────────────────────────────────────── */
[data-testid="stForm"] {{
    background: {WHITE};
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(10,51,112,0.06);
}}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    border-radius: 8px;
    border: 1px solid {GRAY_200};
    font-family: Tahoma, 'Inter', sans-serif;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {{
    border-color: {LIGHT_BLUE};
    box-shadow: 0 0 0 2px rgba(24,146,223,0.15);
}}

/* Input labels */
.stTextInput > label,
.stNumberInput > label,
.stDateInput > label,
.stSelectbox > label,
.stMultiSelect > label {{
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 500;
    color: {NAVY};
    font-size: 0.85rem;
}}

/* ─── Tabs ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    background: {GRAY_50};
    border-radius: 10px;
    padding: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 0.5rem 1.25rem;
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 500;
    color: {GRAY_600};
    background: transparent;
    border: none;
}}
.stTabs [aria-selected="true"] {{
    background: {WHITE} !important;
    color: {NAVY} !important;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(10,51,112,0.1);
}}
.stTabs [data-baseweb="tab-highlight"] {{
    display: none;
}}
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}

/* ─── Dataframes ──────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {GRAY_200};
    border-radius: 12px;
    overflow: hidden;
}}

/* ─── Dividers ────────────────────────────────────────────────── */
hr {{
    border: none;
    border-top: 1px solid {GRAY_200};
    margin: 1.5rem 0;
}}

/* ─── Download button ─────────────────────────────────────────── */
.stDownloadButton > button {{
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 500;
    border-radius: 8px;
    border: 1px solid {LIGHT_BLUE};
    color: {LIGHT_BLUE};
    background: transparent;
}}
.stDownloadButton > button:hover {{
    background: {LIGHT_BLUE};
    color: {WHITE};
}}

/* ─── Alerts / callouts ───────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 10px;
    font-family: Tahoma, 'Inter', sans-serif;
}}

/* ─── Checkbox ────────────────────────────────────────────────── */
.stCheckbox label {{
    font-family: Tahoma, 'Inter', sans-serif;
    font-weight: 500;
}}
</style>
"""


def apply_branding() -> None:
    """Inject CCR enterprise CSS and render the sidebar logo."""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    # Logo in sidebar
    with st.sidebar:
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), width="stretch")
        else:
            st.markdown(
                """
                <div style="text-align:center;padding:0.5rem 0 1rem;">
                    <div style="font-size:1.5rem;font-weight:700;color:white;
                                font-family:Tahoma,sans-serif;">
                        Cypress Creek Solutions
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div style="text-align:center;font-size:0.75rem;'
            'color:rgba(255,255,255,0.6);font-family:Tahoma,sans-serif;'
            'margin-top:-0.5rem;padding-bottom:1rem;">'
            "Workforce Planning</div>",
            unsafe_allow_html=True,
        )


def section_header(title: str, subtitle: str | None = None) -> None:
    """Render a styled section header with optional subtitle."""
    st.markdown(
        f'<h3 style="margin-bottom:0.25rem;">{title}</h3>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)


def status_badge(text: str, color: str = TEAL) -> str:
    """Return HTML for an inline status badge."""
    return (
        f'<span style="background:{color};color:white;padding:0.2rem 0.75rem;'
        f'border-radius:20px;font-size:0.75rem;font-weight:600;'
        f'font-family:Tahoma,sans-serif;">{text}</span>'
    )
