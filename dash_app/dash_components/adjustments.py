"""Dynamic headcount adjustment inputs for Dash."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def adjustment_inputs_layout(
    regions: list[str],
    saved_adjustments: dict[str, int],
) -> html.Div:
    """Return a grid of number inputs, one per region.

    Each input uses a pattern-matching ID:
        {"type": "hc-adj", "region": <region_name>}
    """
    children = []
    for region in regions:
        children.append(
            dbc.Col(
                [
                    html.Label(region, style={"fontSize": "0.82rem"}),
                    dcc.Input(
                        id={"type": "hc-adj", "region": region},
                        type="number",
                        value=int(saved_adjustments.get(region, 0)),
                        min=-100,
                        step=1,
                        className="dash-input",
                        style={"width": "100%"},
                    ),
                ],
                xs=6,
                md=4,
                className="mb-2",
            )
        )
    return html.Div(dbc.Row(children, className="g-2"))
