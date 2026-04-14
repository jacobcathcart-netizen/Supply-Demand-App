"""Dash application factory and entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any other imports that may need credentials
load_dotenv(Path(__file__).parent / ".env")

# Allow imports from the parent directory (config, logic/)
_parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _parent_dir)

# Patch: logic/sensitivity.py imports _monthly_totals from components.visuals
# which depends on Streamlit.  Redirect that import to our local monthly_totals
# module which has no Streamlit dependency.
import types

_dash_app_dir = str(Path(__file__).resolve().parent)
if _dash_app_dir not in sys.path:
    sys.path.insert(0, _dash_app_dir)

from monthly_totals import monthly_totals as _mt  # noqa: E402

# Create a fake "components.visuals" module that exposes _monthly_totals
_fake_visuals = types.ModuleType("components.visuals")
_fake_visuals._monthly_totals = _mt
sys.modules["components.visuals"] = _fake_visuals


# Also stub out the data.snowflake module so logic/scenario.py uses our adapter
import data_adapter as _da  # noqa: E402

_fake_snowflake = types.ModuleType("data.snowflake")
for _fn_name in (
    "get_supply", "get_demand", "get_demand_weight", "get_working_days",
    "get_backlog", "get_cm_backlog", "get_pm_backlog", "get_projects",
    "get_regions_df", "get_connection_info", "reset_connection",
):
    setattr(_fake_snowflake, _fn_name, getattr(_da, _fn_name))
sys.modules["data.snowflake"] = _fake_snowflake
sys.modules["data"] = types.ModuleType("data")

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    assets_folder="assets",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Supply & Demand | CCR",
    update_title=None,
)
server = app.server

# ── Root layout ────────────────────────────────────────────────────
from dash_components.navbar import navbar  # noqa: E402

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh="callback-nav"),
        # ── Session stores ─────────────────────────────────────────
        dcc.Store(id="scenario-store", storage_type="session"),
        dcc.Store(id="projects-store", storage_type="session"),
        # ── Page shell ─────────────────────────────────────────────
        navbar,
        html.Div(dash.page_container, className="page-container"),
    ]
)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
