"""Plotly chart builders for the Supply & Demand Dash app.

All charts use the CCR brand palette and return ``plotly.graph_objects.Figure``.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from monthly_totals import monthly_totals, padded_limits, split_base_adjusted

# ── CCR Brand Colors ───────────────────────────────────────────────
NAVY = "#0a3370"
LIGHT_BLUE = "#008bc1"
YELLOW = "#f5ac1c"
LIGHT_GRAY = "#ebebeb"
GRAY = "#333333"
TEAL = "#33CCA6"
ORANGE = "#F26419"
GOLD = "#F9A620"
GREEN = "#007647"
BLUE = "#2C31A6"
WARM_WHITE = "#FAFAFA"
WHITE = "#FFFFFF"

CHART_COLORS = [LIGHT_BLUE, NAVY, TEAL, ORANGE, GOLD, GREEN, BLUE]

# ── Shared Plotly layout template ──────────────────────────────────

_LAYOUT = dict(
    font=dict(family="Tahoma, Geneva, sans-serif", color=NAVY, size=12),
    paper_bgcolor=WARM_WHITE,
    plot_bgcolor=WARM_WHITE,
    xaxis=dict(
        gridcolor=LIGHT_GRAY,
        gridwidth=0.4,
        showline=False,
        tickfont=dict(color=GRAY, size=10),
    ),
    yaxis=dict(
        gridcolor=LIGHT_GRAY,
        gridwidth=0.4,
        showline=False,
        tickfont=dict(color=GRAY, size=10),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=10),
    ),
    title=dict(font=dict(size=14, color=NAVY)),
    hovermode="x unified",
    margin=dict(l=60, r=30, t=50, b=50),
)


def _base_layout(**overrides) -> dict:
    layout = {**_LAYOUT}
    layout.update(overrides)
    return layout


def _fmt(val: float) -> str:
    if abs(val) >= 1000:
        return f"{val / 1000:,.1f}k"
    return f"{val:,.0f}"


# ── Line chart (shared for baseline / scenario) ───────────────────


def _line_chart(
    df: pd.DataFrame,
    supply_col: str,
    gap_col: str,
    title_prefix: str,
    region_label: str,
    monthly_df: pd.DataFrame | None = None,
    adjustment_start_date=None,
    demand_col: str = "DEMAND",
) -> go.Figure | None:
    if monthly_df is None:
        monthly_df = monthly_totals(df)
    if monthly_df.empty:
        return None

    if demand_col not in monthly_df.columns:
        demand_col = "DEMAND"

    dates = monthly_df["DATE"]
    fig = go.Figure()

    # Supply line
    fig.add_trace(go.Scatter(
        x=dates, y=monthly_df[supply_col],
        mode="lines+markers",
        marker=dict(size=8, color=WARM_WHITE, line=dict(color=LIGHT_BLUE, width=2)),
        line=dict(color=LIGHT_BLUE, width=2.5),
        name=f"{title_prefix} Supply",
    ))
    # Demand line
    fig.add_trace(go.Scatter(
        x=dates, y=monthly_df[demand_col],
        mode="lines+markers",
        marker=dict(size=7, symbol="diamond", color=WARM_WHITE, line=dict(color=ORANGE, width=2)),
        line=dict(color=ORANGE, width=2.5),
        name="Demand",
    ))
    # Gap line
    fig.add_trace(go.Scatter(
        x=dates, y=monthly_df[gap_col],
        mode="lines+markers",
        marker=dict(size=6, symbol="square", color=WARM_WHITE, line=dict(color=NAVY, width=2)),
        line=dict(color=NAVY, width=2, dash="dash"),
        opacity=0.8,
        name=f"{title_prefix} Gap",
    ))
    # Fill between supply and demand
    x_fill = list(dates) + list(dates[::-1])
    y_fill = list(monthly_df[supply_col]) + list(monthly_df[demand_col][::-1])
    fig.add_trace(go.Scatter(
        x=x_fill,
        y=y_fill,
        fill="toself",
        fillcolor="rgba(0,139,193,0.08)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))
    # Zero line
    fig.add_hline(y=0, line_width=0.8, line_color=GRAY, opacity=0.3)

    if adjustment_start_date is not None:
        adj_str = str(adjustment_start_date)[:10]
        adj_str = adj_str[:8] + "01"  # first of month
        fig.add_shape(
            type="line", x0=adj_str, x1=adj_str, y0=0, y1=1,
            yref="paper", line=dict(color=YELLOW, width=1.5, dash="dash"),
            opacity=0.7,
        )
        fig.add_annotation(
            x=adj_str, y=1, yref="paper", text="HC Adj. Start",
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=9, color=NAVY, family="Tahoma"),
        )

    fig.update_layout(
        **_base_layout(
            title=dict(text=f"{title_prefix} Supply vs Demand — {region_label}"),
            yaxis_title="Hours",
        )
    )
    return fig


def baseline_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
    monthly_df: pd.DataFrame | None = None,
) -> go.Figure | None:
    return _line_chart(df, "BASE_SUPPLY", "BASE_GAP", "Baseline", region_label, monthly_df=monthly_df)


def scenario_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
    monthly_df: pd.DataFrame | None = None,
    adjustment_start_date=None,
) -> go.Figure | None:
    return _line_chart(
        df, "SCENARIO_SUPPLY", "SCENARIO_GAP", "Scenario", region_label,
        monthly_df=monthly_df, adjustment_start_date=adjustment_start_date,
        demand_col="SCENARIO_DEMAND",
    )


# ── Gap bar chart ──────────────────────────────────────────────────


def gap_bar_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
    monthly_df: pd.DataFrame | None = None,
) -> go.Figure | None:
    if monthly_df is None:
        monthly_df = monthly_totals(df, backlog=backlog)
    if monthly_df.empty:
        return None

    base_months, adjusted_months = split_base_adjusted(monthly_df)
    fig = go.Figure()

    # Baseline gap bars
    if not base_months.empty:
        fig.add_trace(go.Bar(
            x=base_months["DATE"], y=base_months["DISPLAY_GAP"],
            marker_color=LIGHT_BLUE, opacity=0.85,
            name="Baseline Gap",
            text=[_fmt(v) for v in base_months["DISPLAY_GAP"]],
            textposition="outside",
            textfont=dict(size=8, color=NAVY, family="Tahoma"),
        ))
    # Scenario gap bars
    if not adjusted_months.empty:
        fig.add_trace(go.Bar(
            x=adjusted_months["DATE"], y=adjusted_months["DISPLAY_GAP"],
            marker_color=TEAL, opacity=0.85,
            name="Scenario Gap",
            text=[_fmt(v) for v in adjusted_months["DISPLAY_GAP"]],
            textposition="outside",
            textfont=dict(size=8, color=NAVY, family="Tahoma"),
        ))

    fig.add_hline(y=0, line_width=0.8, line_color=NAVY, opacity=0.4)

    fig.update_layout(
        **_base_layout(
            title=dict(text=f"Supply vs Demand Gap — {region_label}"),
            yaxis_title="Gap (hrs)",
            barmode="group",
            legend=dict(
                orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5,
            ),
        )
    )
    return fig


# ── Backlog trend chart (dual axis) ───────────────────────────────


def backlog_trend_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
    monthly_df: pd.DataFrame | None = None,
    adjustment_start_date=None,
) -> go.Figure | None:
    if monthly_df is None:
        monthly_df = monthly_totals(df, backlog=backlog)
    if monthly_df.empty:
        return None

    monthly_df = monthly_df.assign(
        NORMALIZED_BACKLOG=monthly_df["SCENARIO_GAP_CUMSUM"]
        / monthly_df["SCENARIO_SUPPLY"].replace(0, float("nan"))
    )

    dates = monthly_df["DATE"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Cumulative backlog (left axis)
    fig.add_trace(
        go.Scatter(
            x=dates, y=monthly_df["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers+text",
            marker=dict(size=8, color=WHITE, line=dict(color=ORANGE, width=2)),
            line=dict(color=ORANGE, width=2.5),
            name="Cumulative Backlog (hrs)",
            text=[_fmt(v) for v in monthly_df["SCENARIO_GAP_CUMSUM"]],
            textposition="top center",
            textfont=dict(size=8, color=NAVY),
        ),
        secondary_y=False,
    )
    # Fill under cumulative backlog
    fig.add_trace(
        go.Scatter(
            x=dates, y=monthly_df["SCENARIO_GAP_CUMSUM"],
            fill="tozeroy",
            fillcolor="rgba(242,100,25,0.08)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        secondary_y=False,
    )

    # Normalized backlog (right axis)
    fig.add_trace(
        go.Scatter(
            x=dates, y=monthly_df["NORMALIZED_BACKLOG"],
            mode="lines+markers+text",
            marker=dict(size=7, symbol="square", color=WHITE, line=dict(color=GOLD, width=2)),
            line=dict(color=GOLD, width=2, dash="dash"),
            name="Normalized Backlog (Squad-Months)",
            text=[f"{v:.1f}" for v in monthly_df["NORMALIZED_BACKLOG"].fillna(0)],
            textposition="bottom center",
            textfont=dict(size=8, color=NAVY),
        ),
        secondary_y=True,
    )

    if adjustment_start_date is not None:
        adj_str = str(adjustment_start_date)[:8] + "01"
        fig.add_shape(
            type="line", x0=adj_str, x1=adj_str, y0=0, y1=1,
            yref="paper", line=dict(color=YELLOW, width=1.5, dash="dash"),
            opacity=0.7,
        )
        fig.add_annotation(
            x=adj_str, y=1, yref="paper", text="HC Adj. Start",
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=9, color=NAVY),
        )

    fig.update_layout(
        **_base_layout(
            title=dict(text=f"Backlog Trend — {region_label}"),
            legend=dict(
                orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5,
            ),
        ),
    )
    fig.update_yaxes(
        title_text="Cumulative Backlog (hrs)", secondary_y=False,
        title_font=dict(color=ORANGE), tickfont=dict(color=ORANGE),
        gridcolor=LIGHT_GRAY, gridwidth=0.4,
    )
    fig.update_yaxes(
        title_text="Normalized Backlog (Squad-Months)", secondary_y=True,
        title_font=dict(color=GOLD), tickfont=dict(color=GOLD),
        showgrid=False,
    )
    return fig


# ── Sensitivity fan chart ──────────────────────────────────────────


def sensitivity_fan_chart(
    base_monthly: pd.DataFrame,
    envelope_min: pd.Series,
    envelope_max: pd.Series,
    param_results: list,
    region_label: str = "All regions",
    adjustment_start_date=None,
) -> go.Figure | None:
    if base_monthly.empty:
        return None

    dates = base_monthly["DATE"]
    base_backlog = base_monthly["SCENARIO_GAP_CUMSUM"]

    fig = go.Figure()

    # Envelope (filled region)
    x_env = list(dates) + list(dates[::-1])
    y_env = list(envelope_max.values) + list(envelope_min.values[::-1])
    fig.add_trace(go.Scatter(
        x=x_env,
        y=y_env,
        fill="toself",
        fillcolor="rgba(235,235,235,0.4)",
        line=dict(width=0),
        name="Sensitivity range",
        hoverinfo="skip",
    ))

    # Individual param low/high lines
    colors = CHART_COLORS[:]
    for i, pr in enumerate(param_results):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=pr.low_monthly["DATE"], y=pr.low_monthly["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers",
            marker=dict(size=4, color=WARM_WHITE, line=dict(color=color, width=1.5)),
            line=dict(color=color, width=1, dash="dash"),
            opacity=0.5,
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=pr.high_monthly["DATE"], y=pr.high_monthly["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers",
            marker=dict(size=4, color=WARM_WHITE, line=dict(color=color, width=1.5)),
            line=dict(color=color, width=1, dash="dash"),
            opacity=0.5,
            name=f"{pr.name} (\u00b1)",
        ))

    # Base case line (on top)
    fig.add_trace(go.Scatter(
        x=dates, y=base_backlog,
        mode="lines+markers+text",
        marker=dict(size=8, color=WARM_WHITE, line=dict(color=ORANGE, width=2)),
        line=dict(color=ORANGE, width=2.5),
        name="Base case",
        text=[_fmt(v) for v in base_backlog],
        textposition="top center",
        textfont=dict(size=8, color=NAVY),
    ))

    fig.add_hline(y=0, line_width=0.8, line_color=GRAY, opacity=0.3)

    if adjustment_start_date is not None:
        adj_str = str(adjustment_start_date)[:8] + "01"
        fig.add_shape(
            type="line", x0=adj_str, x1=adj_str, y0=0, y1=1,
            yref="paper", line=dict(color=YELLOW, width=1.5, dash="dash"),
            opacity=0.7,
        )

    fig.update_layout(
        **_base_layout(
            title=dict(text=f"Backlog Sensitivity — {region_label}"),
            yaxis_title="Cumulative Backlog (hrs)",
            legend=dict(
                orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5,
            ),
        )
    )
    return fig


# ── Sensitivity tornado chart ──────────────────────────────────────


def sensitivity_tornado_chart(
    param_results: list,
    base_ending_backlog: float,
) -> go.Figure | None:
    if not param_results:
        return None

    sorted_params = sorted(
        param_results,
        key=lambda p: abs(p.high_ending_backlog - p.low_ending_backlog),
    )

    names = [p.name for p in sorted_params]
    lows = [p.low_ending_backlog for p in sorted_params]
    highs = [p.high_ending_backlog for p in sorted_params]

    low_widths = [low - base_ending_backlog for low in lows]
    high_widths = [high - base_ending_backlog for high in highs]

    fig = go.Figure()

    # Low scenario bars
    fig.add_trace(go.Bar(
        y=names, x=low_widths, base=base_ending_backlog,
        orientation="h",
        marker_color=LIGHT_BLUE,
        name="Low scenario",
        text=[_fmt(v) for v in lows],
        textposition="outside",
        textfont=dict(size=9, color=NAVY),
    ))
    # High scenario bars
    fig.add_trace(go.Bar(
        y=names, x=high_widths, base=base_ending_backlog,
        orientation="h",
        marker_color=ORANGE,
        name="High scenario",
        text=[_fmt(v) for v in highs],
        textposition="outside",
        textfont=dict(size=9, color=NAVY),
    ))

    # Base case reference line
    fig.add_vline(
        x=base_ending_backlog, line_width=1.5, line_color=NAVY, line_dash="dash",
        opacity=0.7,
        annotation_text=f"Base ({_fmt(base_ending_backlog)})",
        annotation_position="top",
        annotation_font=dict(size=9, color=NAVY),
    )

    chart_height = min(max(250, len(names) * 60), 600)
    layout = _base_layout(
        title=dict(text="Impact on Ending Backlog"),
        xaxis_title="Ending Backlog (hrs)",
        barmode="overlay",
        height=chart_height,
        legend=dict(
            orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5,
        ),
    )
    layout["xaxis"] = {**layout.get("xaxis", {}), "gridcolor": LIGHT_GRAY, "gridwidth": 0.4}
    layout["yaxis"] = {**layout.get("yaxis", {}), "showgrid": False}
    fig.update_layout(**layout)
    return fig


# ── Backlog preview charts ─────────────────────────────────────────


def backlog_by_region_chart(by_region: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of backlog hours by region."""
    fig = go.Figure(go.Bar(
        y=by_region["REGION"], x=by_region["HOURS"],
        orientation="h",
        marker_color=LIGHT_BLUE,
        text=[_fmt(v) for v in by_region["HOURS"]],
        textposition="outside",
        textfont=dict(size=9, color=NAVY),
    ))
    fig.update_layout(
        **_base_layout(
            title=dict(text="Backlog Hours by Region"),
            height=max(250, len(by_region) * 35),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=120, r=60, t=40, b=20),
        )
    )
    return fig


def pm_cm_breakdown_chart(breakdown: pd.DataFrame) -> go.Figure:
    """Stacked horizontal bar chart of PM vs CM hours by region."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=breakdown["REGION"], x=breakdown["PM_HRS"],
        orientation="h",
        marker_color=NAVY,
        name="PM",
    ))
    fig.add_trace(go.Bar(
        y=breakdown["REGION"], x=breakdown["CM_HRS"],
        orientation="h",
        marker_color=YELLOW,
        name="CM",
    ))
    fig.update_layout(
        **_base_layout(
            title=dict(text="PM vs CM Hours by Region"),
            barmode="stack",
            height=max(250, len(breakdown) * 35),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=120, r=40, t=40, b=20),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        )
    )
    return fig
