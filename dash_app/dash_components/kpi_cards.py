"""KPI metric card components for Dash."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: str = "normal",
) -> html.Div:
    """Render a single KPI metric card.

    Parameters
    ----------
    label : display label (e.g. "Baseline Supply")
    value : formatted value string (e.g. "12,345 hrs")
    delta : optional delta string (e.g. "+1,200")
    delta_color : "normal" (green=positive) or "inverse" (green=negative)
    """
    children = [
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
    ]
    if delta is not None:
        is_positive = delta.strip().startswith("+")
        if delta_color == "inverse":
            css_class = "kpi-delta negative" if is_positive else "kpi-delta positive"
        else:
            css_class = "kpi-delta positive" if is_positive else "kpi-delta negative"
        children.append(html.Div(delta, className=css_class))

    return html.Div(children, className="kpi-card")


def kpi_row(cards: list[html.Div]) -> dbc.Row:
    """Arrange KPI cards in a responsive row."""
    cols = [dbc.Col(card, xs=6, md=3, className="mb-3") for card in cards]
    return dbc.Row(cols, className="g-3")
