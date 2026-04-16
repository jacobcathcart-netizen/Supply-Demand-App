"""Plotly chart builders for the Supply & Demand app.

All charts use the CCR brand palette and a clean, enterprise aesthetic.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.branding import (
    CHART_COLORS,
    GOLD,
    GRAY,
    LIGHT_BLUE,
    LIGHT_GRAY,
    NAVY,
    ORANGE,
    TEAL,
    WARM_WHITE,
    YELLOW,
)

# ── Plotly template ────────────────────────────────────────────────────

_CCR_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Tahoma, DejaVu Sans, sans-serif", color=NAVY),
        paper_bgcolor=WARM_WHITE,
        plot_bgcolor=WARM_WHITE,
        title=dict(font=dict(size=14, color=NAVY), x=0.5, xanchor="center"),
        xaxis=dict(
            gridcolor=LIGHT_GRAY,
            gridwidth=0.4,
            showgrid=False,
            linecolor=LIGHT_GRAY,
        ),
        yaxis=dict(
            gridcolor=LIGHT_GRAY,
            gridwidth=0.4,
            griddash="dash",
            showgrid=True,
            linecolor=LIGHT_GRAY,
            zeroline=True,
            zerolinecolor=GRAY,
            zerolinewidth=0.8,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=10),
        ),
        margin=dict(l=60, r=30, t=50, b=50),
        hovermode="x unified",
    )
)


# ── Shared helpers ───────────────────────────────────────────────────


def _monthly_totals(df: pd.DataFrame, backlog: float = 0) -> pd.DataFrame:
    """Aggregate scenario results to monthly level and compute cumulative backlog."""
    if df.empty:
        return pd.DataFrame()

    backlog = float(backlog)

    agg_cols = [
        "BASE_SUPPLY",
        "SCENARIO_SUPPLY",
        "DEMAND",
        "BASE_GAP",
        "SCENARIO_GAP",
        "SUPPLY_DELTA",
    ]
    if "SCENARIO_DEMAND" in df.columns:
        agg_cols.insert(3, "SCENARIO_DEMAND")

    monthly = (
        df.groupby("DATE", as_index=False)[agg_cols]
        .sum()
        .sort_values("DATE")
    )
    monthly["DATE"] = pd.to_datetime(monthly["DATE"])

    base_gap = pd.to_numeric(monthly["BASE_GAP"], errors="coerce")
    scen_gap = pd.to_numeric(monthly["SCENARIO_GAP"], errors="coerce")

    base_cumsum = []
    scen_cumsum = []
    prev_base = 0.0
    prev_scen = backlog
    for b, s in zip(base_gap, scen_gap):
        prev_base = max(prev_base - b, 0.0)
        prev_scen = max(prev_scen - s, 0.0)
        base_cumsum.append(prev_base)
        scen_cumsum.append(prev_scen)

    monthly["BASE_GAP_CUMSUM"] = base_cumsum
    monthly["SCENARIO_GAP_CUMSUM"] = scen_cumsum
    monthly["BACKLOG_AS_SUPPLY"] = (
        monthly["SCENARIO_GAP_CUMSUM"]
        / monthly["SCENARIO_SUPPLY"].replace(0, float("nan"))
    )
    return monthly


def _fmt_hrs(val: float) -> str:
    """Format hours as compact string (e.g. 1.2k, 15k)."""
    if abs(val) >= 1000:
        return f"{val / 1000:,.1f}k"
    return f"{val:,.0f}"


def _date_labels(monthly: pd.DataFrame) -> list[str]:
    """Return month labels for x-axis."""
    return monthly["DATE"].dt.strftime("%b %Y").tolist()


# ── Baseline & scenario line charts ─────────────────────────────────


def _line_chart(
    df: pd.DataFrame,
    supply_col: str,
    gap_col: str,
    title_prefix: str,
    region_label: str,
    monthly: pd.DataFrame | None = None,
    adjustment_start_date=None,
    demand_col: str = "DEMAND",
) -> go.Figure | None:
    """Shared implementation for baseline / scenario supply-vs-demand charts."""
    if monthly is None:
        monthly = _monthly_totals(df)
    if monthly.empty:
        return None

    if demand_col not in monthly.columns:
        demand_col = "DEMAND"

    dates = monthly["DATE"]
    x_labels = _date_labels(monthly)

    fig = go.Figure()

    # Supply line
    fig.add_trace(go.Scatter(
        x=dates,
        y=monthly[supply_col],
        mode="lines+markers+text",
        name=f"{title_prefix} Supply",
        line=dict(color=LIGHT_BLUE, width=2.5),
        marker=dict(size=8, color=WARM_WHITE, line=dict(color=LIGHT_BLUE, width=2)),
        text=[_fmt_hrs(v) for v in monthly[supply_col]],
        textposition="top center",
        textfont=dict(size=9, color=LIGHT_BLUE, family="Tahoma"),
    ))

    # Demand line
    fig.add_trace(go.Scatter(
        x=dates,
        y=monthly[demand_col],
        mode="lines+markers+text",
        name="Demand",
        line=dict(color=ORANGE, width=2.5),
        marker=dict(size=7, color=WARM_WHITE, line=dict(color=ORANGE, width=2), symbol="diamond"),
        text=[_fmt_hrs(v) for v in monthly[demand_col]],
        textposition="bottom center",
        textfont=dict(size=9, color=ORANGE, family="Tahoma"),
    ))

    # Fill between supply and demand
    fig.add_trace(go.Scatter(
        x=pd.concat([dates, dates[::-1]]),
        y=pd.concat([monthly[supply_col], monthly[demand_col][::-1]]),
        fill="toself",
        fillcolor=f"rgba(0,139,193,0.08)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Gap line
    fig.add_trace(go.Scatter(
        x=dates,
        y=monthly[gap_col],
        mode="lines+markers+text",
        name=f"{title_prefix} Gap",
        line=dict(color=NAVY, width=2, dash="dash"),
        marker=dict(size=6, color=WARM_WHITE, line=dict(color=NAVY, width=2), symbol="square"),
        text=[_fmt_hrs(v) for v in monthly[gap_col]],
        textposition="bottom center",
        textfont=dict(size=9, color=NAVY, family="Tahoma"),
    ))

    # Adjustment start indicator
    if adjustment_start_date is not None:
        adj_dt = pd.Timestamp(adjustment_start_date).normalize().replace(day=1)
        fig.add_vline(
            x=adj_dt,
            line_width=1.5,
            line_dash="dash",
            line_color=YELLOW,
            opacity=0.7,
            annotation_text="HC Adj. Start",
            annotation_position="top right",
            annotation_font=dict(size=9, color=NAVY, family="Tahoma"),
        )

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title=f"{title_prefix} Supply vs Demand — {region_label}",
        yaxis_title="Hours",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=450,
    )

    return fig


def baseline_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
    monthly: pd.DataFrame | None = None,
) -> go.Figure | None:
    return _line_chart(df, "BASE_SUPPLY", "BASE_GAP", "Baseline", region_label, monthly=monthly)


def scenario_supply_demand_with_gap(
    df: pd.DataFrame,
    region_label: str = "All regions",
    monthly: pd.DataFrame | None = None,
    adjustment_start_date=None,
) -> go.Figure | None:
    return _line_chart(
        df, "SCENARIO_SUPPLY", "SCENARIO_GAP", "Scenario", region_label,
        monthly=monthly, adjustment_start_date=adjustment_start_date,
        demand_col="SCENARIO_DEMAND",
    )


# ── Gap bar chart ────────────────────────────────────────────────────


def gap_bar_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
    monthly: pd.DataFrame | None = None,
) -> go.Figure | None:
    """Baseline vs scenario gap as grouped bars with data labels."""
    if monthly is None:
        monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    # Determine which months have adjustments
    is_adjusted = monthly["SUPPLY_DELTA"] != 0
    display_gap = monthly["SCENARIO_GAP"].where(is_adjusted, monthly["BASE_GAP"])

    dates = monthly["DATE"]

    fig = go.Figure()

    # Baseline gap bars (months without adjustment)
    base_mask = ~is_adjusted
    if base_mask.any():
        fig.add_trace(go.Bar(
            x=dates[base_mask],
            y=monthly["BASE_GAP"][base_mask],
            name="Baseline Gap",
            marker_color=LIGHT_BLUE,
            opacity=0.85,
            text=[_fmt_hrs(v) for v in monthly["BASE_GAP"][base_mask]],
            textposition="outside",
            textfont=dict(size=9, color=NAVY, family="Tahoma"),
        ))

    # Scenario gap bars (months with adjustment)
    adj_mask = is_adjusted
    if adj_mask.any():
        fig.add_trace(go.Bar(
            x=dates[adj_mask],
            y=display_gap[adj_mask],
            name="Scenario Gap",
            marker_color=TEAL,
            opacity=0.85,
            text=[_fmt_hrs(v) for v in display_gap[adj_mask]],
            textposition="outside",
            textfont=dict(size=9, color=NAVY, family="Tahoma"),
        ))

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title=f"Supply vs Demand Gap — {region_label}",
        yaxis_title="Gap (hrs)",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=450,
    )

    return fig


# ── Backlog trend chart ──────────────────────────────────────────────


def backlog_trend_chart(
    df: pd.DataFrame,
    region_label: str = "All regions",
    backlog: float = 0,
    monthly: pd.DataFrame | None = None,
    adjustment_start_date=None,
) -> go.Figure | None:
    """Cumulative backlog (hours) on left axis, normalised backlog on right axis."""
    if monthly is None:
        monthly = _monthly_totals(df, backlog=backlog)
    if monthly.empty:
        return None

    monthly = monthly.assign(
        NORMALIZED_BACKLOG=monthly["SCENARIO_GAP_CUMSUM"]
        / monthly["SCENARIO_SUPPLY"].replace(0, float("nan"))
    )

    dates = monthly["DATE"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Cumulative backlog (left axis)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=monthly["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers+text",
            name="Cumulative Backlog (hrs)",
            line=dict(color=ORANGE, width=2.5),
            marker=dict(size=8, color="white", line=dict(color=ORANGE, width=2)),
            text=[_fmt_hrs(v) for v in monthly["SCENARIO_GAP_CUMSUM"]],
            textposition="top center",
            textfont=dict(size=9, color=NAVY, family="Tahoma"),
            fill="tozeroy",
            fillcolor="rgba(242,100,25,0.08)",
        ),
        secondary_y=False,
    )

    # Normalized backlog (right axis)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=monthly["NORMALIZED_BACKLOG"],
            mode="lines+markers+text",
            name="Normalized Backlog (Squad-Months)",
            line=dict(color=GOLD, width=2, dash="dash"),
            marker=dict(size=7, color="white", line=dict(color=GOLD, width=2), symbol="square"),
            text=[f"{v:.1f}" for v in monthly["NORMALIZED_BACKLOG"]],
            textposition="bottom center",
            textfont=dict(size=9, color=NAVY, family="Tahoma"),
        ),
        secondary_y=True,
    )

    # Adjustment indicator
    if adjustment_start_date is not None:
        adj_dt = pd.Timestamp(adjustment_start_date).normalize().replace(day=1)
        fig.add_vline(
            x=adj_dt,
            line_width=1.5,
            line_dash="dash",
            line_color=YELLOW,
            opacity=0.7,
            annotation_text="HC Adj. Start",
            annotation_position="top right",
            annotation_font=dict(size=9, color=NAVY, family="Tahoma"),
        )

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title=f"Backlog Trend — {region_label}",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=450,
    )
    fig.update_yaxes(title_text="Cumulative Backlog (hrs)", secondary_y=False, color=ORANGE)
    fig.update_yaxes(title_text="Normalized Backlog (Squad-Months)", secondary_y=True, color=GOLD)

    return fig


# ── Sensitivity charts ───────────────────────────────────────────────


def sensitivity_fan_chart(
    base_monthly: pd.DataFrame,
    envelope_min: pd.Series,
    envelope_max: pd.Series,
    param_results: list,
    region_label: str = "All regions",
    adjustment_start_date=None,
) -> go.Figure | None:
    """Fan chart: base backlog trend with shaded sensitivity envelope."""
    if base_monthly.empty:
        return None

    dates = base_monthly["DATE"]
    base_backlog = base_monthly["SCENARIO_GAP_CUMSUM"]

    fig = go.Figure()

    # Outer envelope
    fig.add_trace(go.Scatter(
        x=pd.concat([dates, dates[::-1]]),
        y=pd.concat([
            pd.Series(envelope_max.values),
            pd.Series(envelope_min.values[::-1]),
        ]),
        fill="toself",
        fillcolor=f"rgba(235,235,235,0.5)",
        line=dict(width=0),
        name="Sensitivity range",
        hoverinfo="skip",
    ))

    # Individual param low/high lines
    colors = CHART_COLORS[:]
    for i, pr in enumerate(param_results):
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatter(
            x=pr.low_monthly["DATE"],
            y=pr.low_monthly["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers",
            line=dict(color=color, width=1, dash="dash"),
            marker=dict(size=4, color=WARM_WHITE, line=dict(color=color, width=1.5)),
            opacity=0.45,
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=pr.high_monthly["DATE"],
            y=pr.high_monthly["SCENARIO_GAP_CUMSUM"],
            mode="lines+markers",
            name=f"{pr.name} (\u00b1)",
            line=dict(color=color, width=1, dash="dash"),
            marker=dict(size=4, color=WARM_WHITE, line=dict(color=color, width=1.5)),
            opacity=0.45,
        ))

    # Base case line (on top)
    fig.add_trace(go.Scatter(
        x=dates,
        y=base_backlog,
        mode="lines+markers+text",
        name="Base case",
        line=dict(color=ORANGE, width=2.5),
        marker=dict(size=8, color=WARM_WHITE, line=dict(color=ORANGE, width=2)),
        text=[_fmt_hrs(v) for v in base_backlog],
        textposition="top center",
        textfont=dict(size=9, color=NAVY, family="Tahoma"),
        fill="tozeroy",
        fillcolor="rgba(242,100,25,0.06)",
    ))

    # Adjustment indicator
    if adjustment_start_date is not None:
        adj_dt = pd.Timestamp(adjustment_start_date).normalize().replace(day=1)
        fig.add_vline(
            x=adj_dt,
            line_width=1.5,
            line_dash="dash",
            line_color=YELLOW,
            opacity=0.7,
            annotation_text="HC Adj. Start",
            annotation_position="top right",
            annotation_font=dict(size=9, color=NAVY, family="Tahoma"),
        )

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title=f"Backlog Sensitivity — {region_label}",
        yaxis_title="Cumulative Backlog (hrs)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        height=500,
    )

    return fig


def sensitivity_tornado_chart(
    param_results: list,
    base_ending_backlog: float,
) -> go.Figure | None:
    """Tornado chart: rank inputs by impact on ending backlog."""
    if not param_results:
        return None

    # Filter out zero-impact parameters
    param_results = [
        p for p in param_results
        if abs(p.high_ending_backlog - p.low_ending_backlog) > 0.01
    ]
    if not param_results:
        return None

    # Sort by total range (widest at top)
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
        y=names,
        x=low_widths,
        base=base_ending_backlog,
        orientation="h",
        name="Low scenario",
        marker_color=LIGHT_BLUE,
        text=[_fmt_hrs(v) for v in lows],
        textposition="outside",
        textfont=dict(size=9, color=NAVY, family="Tahoma"),
    ))

    # High scenario bars
    fig.add_trace(go.Bar(
        y=names,
        x=high_widths,
        base=base_ending_backlog,
        orientation="h",
        name="High scenario",
        marker_color=ORANGE,
        text=[_fmt_hrs(v) for v in highs],
        textposition="outside",
        textfont=dict(size=9, color=NAVY, family="Tahoma"),
    ))

    # Base case reference line
    fig.add_vline(
        x=base_ending_backlog,
        line_width=1.5,
        line_dash="dash",
        line_color=NAVY,
        opacity=0.7,
        annotation_text=f"Base ({_fmt_hrs(base_ending_backlog)})",
        annotation_position="top",
        annotation_font=dict(size=9, color=NAVY, family="Tahoma"),
    )

    chart_height = max(300, len(names) * 60 + 100)

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title="Impact on Ending Backlog",
        xaxis_title="Ending Backlog (hrs)",
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        height=chart_height,
    )
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=True)

    return fig


# ── Backlog preview charts (Inputs page) ────────────────────────────


def backlog_by_region_chart(by_region: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of backlog hours by region."""
    by_region = by_region.sort_values("HOURS", ascending=True)

    fig = go.Figure(go.Bar(
        y=by_region["REGION"],
        x=by_region["HOURS"],
        orientation="h",
        marker_color=LIGHT_BLUE,
        text=[f"{v:,.0f}" for v in by_region["HOURS"]],
        textposition="outside",
        textfont=dict(size=9, color=NAVY, family="Tahoma"),
    ))

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title="Backlog Hours by Region",
        xaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(l=120, r=60, t=50, b=30),
        height=max(250, len(by_region) * 35 + 80),
    )

    return fig


def pm_vs_cm_chart(breakdown: pd.DataFrame) -> go.Figure:
    """Stacked horizontal bar chart of PM vs CM hours by region."""
    breakdown = breakdown.sort_values("REGION")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=breakdown["REGION"],
        x=breakdown["PM_HRS"],
        orientation="h",
        name="PM",
        marker_color=NAVY,
    ))
    fig.add_trace(go.Bar(
        y=breakdown["REGION"],
        x=breakdown["CM_HRS"],
        orientation="h",
        name="CM",
        marker_color=YELLOW,
    ))

    fig.update_layout(
        template=_CCR_TEMPLATE,
        title="PM vs CM Hours by Region",
        barmode="stack",
        xaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=120, r=30, t=50, b=50),
        height=max(250, len(breakdown) * 35 + 80),
    )

    return fig
