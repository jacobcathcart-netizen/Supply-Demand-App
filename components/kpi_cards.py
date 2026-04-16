"""Reusable KPI card components for the Supply & Demand dashboard."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def kpi_card(label: str, value: str, delta: str | None = None) -> dbc.Col:
    """Return a single KPI metric card inside a responsive column."""
    children = [
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
    ]
    if delta:
        children.append(html.Div(delta, className="kpi-delta"))

    return dbc.Col(
        html.Div(children, className="kpi-card"),
        xs=12,
        sm=6,
        md=3,
        className="mb-3",
    )


def kpi_row(metrics: list[dict[str, str]]) -> dbc.Row:
    """Return a row of KPI cards.

    Parameters
    ----------
    metrics:
        List of dicts with keys ``label``, ``value``, and optional ``delta``.
    """
    return dbc.Row(
        [kpi_card(m["label"], m["value"], m.get("delta")) for m in metrics],
        className="g-3",
    )
