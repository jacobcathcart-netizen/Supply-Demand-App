"""CCR corporate branding — colors, fonts, and enterprise CSS."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# ── Asset paths ──────────────────────────────────────────────────────
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_LOGO_PATH = _ASSETS_DIR / "logo.jpg"
HERO_IMAGE_PATH = _ASSETS_DIR / "solar_farm.jpg"

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

# Backward-compat aliases for removed constants
GRAY_50 = LIGHT_GRAY
GRAY_100 = LIGHT_GRAY
GRAY_600 = GRAY

# Chart palette (ordered for visual clarity)
CHART_COLORS = [LIGHT_BLUE, NAVY, TEAL, ORANGE, GOLD, GREEN, BLUE]

# Table alternating row color
TABLE_ALT_ROW = "#D9D9D9"

# ── Custom CSS ───────────────────────────────────────────────────────

_CUSTOM_CSS = f"""
<style>
/* ─── Global font ─────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: Tahoma, Geneva, sans-serif;
}}

/* ─── Hide Streamlit default chrome (keep header for skip-nav a11y) */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}

/* ─── Sidebar collapse/expand button ──────────────────────────── */
[data-testid="stSidebar"][aria-expanded="false"] ~ [data-testid="collapsedControl"] {{
    background: {NAVY};
    border-radius: 0 8px 8px 0;
    box-shadow: 2px 2px 8px rgba(10,51,112,0.25);
}}
[data-testid="collapsedControl"] svg {{
    color: {WHITE} !important;
    width: 1.25rem;
    height: 1.25rem;
}}

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
    color: {YELLOW} !important;
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
    background: rgba(0,139,193,0.2);
    border-left: 3px solid {LIGHT_BLUE};
}}

/* ─── Page header area ────────────────────────────────────────── */
h1 {{
    font-family: Tahoma, Geneva, sans-serif;
    color: {NAVY};
    font-weight: 700;
    letter-spacing: -0.02em;
    padding-bottom: 0.25rem;
    border-bottom: 3px solid {LIGHT_BLUE};
    margin-bottom: 1.5rem;
}}
h2, h3 {{
    font-family: Tahoma, Geneva, sans-serif;
    color: {NAVY};
    font-weight: 600;
}}
h4, h5, h6 {{
    font-family: Tahoma, Geneva, sans-serif;
    color: {GRAY_600};
    font-weight: 600;
}}

/* ─── Metric cards ────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {WHITE};
    border: none;
    border-left: 3px solid {LIGHT_BLUE};
    border-radius: 2px 10px 10px 2px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 8px rgba(10,51,112,0.06);
    transition: box-shadow 0.25s ease, border-left-color 0.25s ease;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: 0 4px 16px rgba(10,51,112,0.1);
    border-left-color: {YELLOW};
}}
[data-testid="stMetricLabel"] {{
    font-family: Tahoma, Geneva, sans-serif;
    color: {GRAY_600};
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] {{
    font-family: Tahoma, Geneva, sans-serif;
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
    font-family: Tahoma, Geneva, sans-serif;
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
    font-family: Tahoma, Geneva, sans-serif;
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s ease;
    border: 1px solid {GRAY_200};
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stFormSubmitButton"] {{
    background: linear-gradient(135deg, {LIGHT_BLUE} 0%, {NAVY} 100%);
    color: {WHITE};
    border: none;
    box-shadow: 0 2px 8px rgba(0,139,193,0.3);
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 16px rgba(0,139,193,0.4);
    transform: translateY(-1px);
}}
.stButton > button[kind="secondary"]:hover {{
    border-color: {LIGHT_BLUE};
    color: {LIGHT_BLUE};
}}

/* ─── Form styling ────────────────────────────────────────────── */
[data-testid="stForm"] {{
    background: transparent;
    border: 1px solid {GRAY_200};
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: none;
}}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    border-radius: 8px;
    border: 1px solid {GRAY_200};
    font-family: Tahoma, Geneva, sans-serif;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {{
    border-color: {LIGHT_BLUE};
    box-shadow: 0 0 0 2px rgba(0,139,193,0.15);
}}

/* Input labels */
.stTextInput > label,
.stNumberInput > label,
.stDateInput > label,
.stSelectbox > label,
.stMultiSelect > label {{
    font-family: Tahoma, Geneva, sans-serif;
    font-weight: 500;
    color: {NAVY};
    font-size: 0.85rem;
}}

/* ─── Tabs ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 2px;
    background: transparent;
    border-bottom: 2px solid {GRAY_200};
    border-radius: 0;
    padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 6px 6px 0 0;
    padding: 0.6rem 1.5rem;
    font-family: Tahoma, Geneva, sans-serif;
    font-weight: 600;
    color: {GRAY};
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: color 0.2s ease, border-color 0.2s ease;
}}
.stTabs [aria-selected="true"] {{
    color: {NAVY} !important;
    font-weight: 700;
    border-bottom-color: {LIGHT_BLUE} !important;
    background: transparent !important;
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
    font-family: Tahoma, Geneva, sans-serif;
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
    font-family: Tahoma, Geneva, sans-serif;
}}

/* ─── Checkbox ────────────────────────────────────────────────── */
.stCheckbox label {{
    font-family: Tahoma, Geneva, sans-serif;
    font-weight: 500;
}}

/* ─── Background texture (faint engineering grid) ────────────── */
[data-testid="stAppViewContainer"] {{
    background-color: {WARM_WHITE};
    background-image:
        linear-gradient(rgba(10,51,112,0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(10,51,112,0.015) 1px, transparent 1px);
    background-size: 40px 40px;
}}

/* ─── Animations ─────────────────────────────────────────────── */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
[data-testid="stMainBlockContainer"] > div {{
    animation: fadeInUp 0.4s ease-out;
}}

@keyframes slideIn {{
    from {{ opacity: 0; transform: translateX(-8px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}
[data-testid="stMetric"] {{
    animation: slideIn 0.3s ease-out both;
}}
[data-testid="stMetric"]:nth-child(1) {{ animation-delay: 0.05s; }}
[data-testid="stMetric"]:nth-child(2) {{ animation-delay: 0.1s; }}
[data-testid="stMetric"]:nth-child(3) {{ animation-delay: 0.15s; }}
[data-testid="stMetric"]:nth-child(4) {{ animation-delay: 0.2s; }}

.stTabs [data-baseweb="tab-panel"] {{
    animation: fadeInUp 0.25s ease-out;
}}

/* ─── Accessibility focus ring ───────────────────────────────── */
*:focus-visible {{
    outline: 2px solid {LIGHT_BLUE};
    outline-offset: 2px;
    border-radius: 4px;
}}
</style>
"""


def apply_branding() -> None:
    """Inject CCR enterprise CSS and render the sidebar logo."""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    # Logo in sidebar
    with st.sidebar:
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), width="stretch", caption="Cypress Creek Renewables")
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
            'color:rgba(255,255,255,0.85);font-family:Tahoma,sans-serif;'
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


def status_badge(text: str, color: str = LIGHT_BLUE) -> str:
    """Return HTML for an inline outlined status badge."""
    return (
        f'<span role="status" style="border:1.5px solid {color};color:{color};'
        f'background:transparent;padding:0.15rem 0.65rem;border-radius:4px;'
        f'font-size:0.72rem;font-weight:700;font-family:Tahoma,Geneva,sans-serif;'
        f'letter-spacing:0.03em;">{text}</span>'
    )
