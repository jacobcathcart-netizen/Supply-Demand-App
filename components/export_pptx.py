"""Export scenario results to a branded CCR PowerPoint presentation.

Generates a multi-slide deck with KPI metrics, chart images, and
enterprise styling using the CCR brand palette.  Accepts Plotly
``go.Figure`` objects and renders them to PNG via kaleido.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from components.branding import (
    GRAY,
    LIGHT_BLUE,
    LIGHT_GRAY,
    NAVY,
    ORANGE,
    WARM_WHITE,
    WHITE,
    YELLOW,
)

# ── Constants ──────────────────────────────────────────────────────────

_SLIDE_WIDTH = Inches(13.333)
_SLIDE_HEIGHT = Inches(7.5)

_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.jpg"

_NAVY = RGBColor.from_string(NAVY.lstrip("#"))
_LIGHT_BLUE = RGBColor.from_string(LIGHT_BLUE.lstrip("#"))
_ORANGE = RGBColor.from_string(ORANGE.lstrip("#"))
_YELLOW = RGBColor.from_string(YELLOW.lstrip("#"))
_WHITE = RGBColor.from_string("FFFFFF")
_GRAY = RGBColor.from_string(GRAY.lstrip("#"))
_LIGHT_GRAY = RGBColor.from_string(LIGHT_GRAY.lstrip("#"))
_WARM_WHITE = RGBColor.from_string(WARM_WHITE.lstrip("#"))

_FONT_FAMILY = "Tahoma"


# ── Helpers ────────────────────────────────────────────────────────────


def _hex_to_rgb(hex_color: str) -> RGBColor:
    return RGBColor.from_string(hex_color.lstrip("#"))


def _set_slide_bg(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_shape(
    slide,
    left: int,
    top: int,
    width: int,
    height: int,
    fill_color: RGBColor | None = None,
    border_color: RGBColor | None = None,
    border_width: Pt | None = None,
) -> Any:
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.shadow.inherit = False

    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()

    if border_color and border_width:
        shape.line.color.rgb = border_color
        shape.line.width = border_width
    else:
        shape.line.fill.background()

    return shape


def _add_text_box(
    slide,
    left: int,
    top: int,
    width: int,
    height: int,
    text: str,
    font_size: int = 12,
    font_color: RGBColor = _NAVY,
    bold: bool = False,
    alignment: PP_ALIGN = PP_ALIGN.LEFT,
    font_name: str = _FONT_FAMILY,
    anchor: MSO_ANCHOR = MSO_ANCHOR.TOP,
) -> Any:
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.text_frame.word_wrap = True
    txBox.text_frame.auto_size = None
    txBox.text_frame.paragraphs[0].alignment = alignment
    txBox.text_frame.paragraphs[0].space_before = Pt(0)
    txBox.text_frame.paragraphs[0].space_after = Pt(0)

    run = (
        txBox.text_frame.paragraphs[0].runs[0]
        if txBox.text_frame.paragraphs[0].runs
        else txBox.text_frame.paragraphs[0].add_run()
    )
    run.text = text
    run.font.size = Pt(font_size)
    run.font.color.rgb = font_color
    run.font.bold = bold
    run.font.name = font_name

    return txBox


def _fig_to_image_stream(fig: go.Figure, width: int = 1200, height: int = 500) -> BytesIO:
    """Render a Plotly Figure to a PNG BytesIO stream via kaleido."""
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    buf = BytesIO(img_bytes)
    buf.seek(0)
    return buf


def _add_logo(slide, left: int, top: int, height: int = Inches(0.6)) -> None:
    if _LOGO_PATH.exists():
        slide.shapes.add_picture(str(_LOGO_PATH), left, top, height=height)


def _add_footer_bar(slide, text: str = "") -> None:
    bar_height = Inches(0.35)
    bar_top = _SLIDE_HEIGHT - bar_height
    _add_shape(slide, 0, bar_top, _SLIDE_WIDTH, bar_height, fill_color=_NAVY)

    if text:
        _add_text_box(
            slide,
            Inches(0.5),
            bar_top + Inches(0.04),
            _SLIDE_WIDTH - Inches(1),
            bar_height - Inches(0.08),
            text,
            font_size=8,
            font_color=_WHITE,
            alignment=PP_ALIGN.RIGHT,
        )


# ── Slide builders ─────────────────────────────────────────────────────


def _build_title_slide(prs, scenario_name, region_label, report_date):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, _NAVY)
    _add_shape(slide, 0, 0, _SLIDE_WIDTH, Inches(0.08), fill_color=_LIGHT_BLUE)
    _add_logo(slide, Inches(0.7), Inches(0.6), height=Inches(1.0))
    _add_text_box(slide, Inches(0.7), Inches(2.2), Inches(10), Inches(1.2), "Supply & Demand", font_size=44, font_color=_WHITE, bold=True)
    _add_text_box(slide, Inches(0.7), Inches(3.2), Inches(10), Inches(0.8), "Scenario Results", font_size=36, font_color=_LIGHT_BLUE, bold=True)
    _add_shape(slide, Inches(0.7), Inches(4.2), Inches(3), Inches(0.04), fill_color=_YELLOW)
    _add_text_box(slide, Inches(0.7), Inches(4.6), Inches(8), Inches(0.4), scenario_name, font_size=18, font_color=_WHITE)
    _add_text_box(slide, Inches(0.7), Inches(5.15), Inches(8), Inches(0.4), f"Region: {region_label}", font_size=14, font_color=_hex_to_rgb("#8EAED0"))
    _add_text_box(slide, Inches(0.7), Inches(5.6), Inches(8), Inches(0.4), report_date, font_size=14, font_color=_hex_to_rgb("#8EAED0"))
    _add_shape(slide, 0, _SLIDE_HEIGHT - Inches(0.08), _SLIDE_WIDTH, Inches(0.08), fill_color=_YELLOW)


def _build_kpi_slide(prs, metrics):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, _hex_to_rgb(WARM_WHITE))
    _add_shape(slide, 0, 0, _SLIDE_WIDTH, Inches(0.9), fill_color=_NAVY)
    _add_text_box(slide, Inches(0.6), Inches(0.15), Inches(8), Inches(0.6), "Key Performance Indicators", font_size=26, font_color=_WHITE, bold=True)
    _add_logo(slide, _SLIDE_WIDTH - Inches(1.8), Inches(0.12), height=Inches(0.65))

    _add_text_box(slide, Inches(0.6), Inches(1.2), Inches(4), Inches(0.4), "SUPPLY & DEMAND", font_size=12, font_color=_LIGHT_BLUE, bold=True)
    _draw_metric_cards(slide, ["Baseline Supply", "Scenario Supply", "Total Demand", "Supply Delta"], metrics, top=Inches(1.7))

    _add_text_box(slide, Inches(0.6), Inches(4.0), Inches(4), Inches(0.4), "GAP & BACKLOG", font_size=12, font_color=_LIGHT_BLUE, bold=True)
    _draw_metric_cards(slide, ["Baseline Gap", "Scenario Gap", "Initial Backlog", "Ending Backlog"], metrics, top=Inches(4.5))

    _add_footer_bar(slide, "Cypress Creek Renewables | Workforce Planning")


def _draw_metric_cards(slide, keys, metrics, top):
    card_width = Inches(2.8)
    card_height = Inches(1.8)
    margin_left = Inches(0.6)
    gap = Inches(0.25)

    for i, key in enumerate(keys):
        m = metrics.get(key, {"value": "N/A", "delta": ""})
        left = margin_left + i * (card_width + gap)
        _add_shape(slide, left, top, card_width, card_height, fill_color=_WHITE)
        _add_shape(slide, left, top, Inches(0.06), card_height, fill_color=_LIGHT_BLUE)
        _add_text_box(slide, left + Inches(0.25), top + Inches(0.2), card_width - Inches(0.4), Inches(0.3), key.upper(), font_size=9, font_color=_GRAY, bold=True)
        _add_text_box(slide, left + Inches(0.25), top + Inches(0.6), card_width - Inches(0.4), Inches(0.6), m["value"], font_size=22, font_color=_NAVY, bold=True)
        if m.get("delta"):
            _add_text_box(slide, left + Inches(0.25), top + Inches(1.25), card_width - Inches(0.4), Inches(0.35), m["delta"], font_size=10, font_color=_GRAY)


def _build_chart_slide(prs, title, fig, caption=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, _hex_to_rgb(WARM_WHITE))
    _add_shape(slide, 0, 0, _SLIDE_WIDTH, Inches(0.9), fill_color=_NAVY)
    _add_text_box(slide, Inches(0.6), Inches(0.15), Inches(10), Inches(0.6), title, font_size=26, font_color=_WHITE, bold=True)
    _add_logo(slide, _SLIDE_WIDTH - Inches(1.8), Inches(0.12), height=Inches(0.65))

    img_stream = _fig_to_image_stream(fig)
    slide.shapes.add_picture(img_stream, Inches(0.3), Inches(1.1), _SLIDE_WIDTH - Inches(0.6), Inches(5.4))

    if caption:
        _add_text_box(slide, Inches(0.6), Inches(6.6), _SLIDE_WIDTH - Inches(1.2), Inches(0.4), caption, font_size=9, font_color=_GRAY)

    _add_footer_bar(slide, "Cypress Creek Renewables | Workforce Planning")


# ── Public API ─────────────────────────────────────────────────────────


def build_presentation(
    *,
    scenario_name: str,
    region_label: str,
    metrics: dict[str, dict[str, str]],
    fig_baseline: go.Figure | None = None,
    fig_scenario: go.Figure | None = None,
    fig_gap: go.Figure | None = None,
    fig_backlog: go.Figure | None = None,
    fig_sensitivity_fan: go.Figure | None = None,
    fig_sensitivity_tornado: go.Figure | None = None,
) -> bytes:
    """Build a complete branded PowerPoint and return raw bytes."""
    prs = Presentation()
    prs.slide_width = _SLIDE_WIDTH
    prs.slide_height = _SLIDE_HEIGHT

    today = date.today().strftime("%B %d, %Y")

    _build_title_slide(prs, scenario_name, region_label, today)
    _build_kpi_slide(prs, metrics)

    if fig_baseline is not None:
        _build_chart_slide(prs, "Baseline Supply vs Demand", fig_baseline, "Baseline supply and demand over time with gap analysis.")
    if fig_scenario is not None:
        _build_chart_slide(prs, "Scenario Supply vs Demand", fig_scenario, "Scenario supply and demand with headcount adjustments applied.")
    if fig_gap is not None:
        _build_chart_slide(prs, "Gap Analysis", fig_gap, "Monthly gap comparison: baseline vs scenario.")
    if fig_backlog is not None:
        _build_chart_slide(prs, "Backlog Trend", fig_backlog, "Cumulative backlog trend with normalized backlog (squad-months).")
    if fig_sensitivity_fan is not None:
        _build_chart_slide(prs, "Sensitivity Analysis", fig_sensitivity_fan, "Backlog sensitivity envelope showing the range of possible outcomes.")
    if fig_sensitivity_tornado is not None:
        _build_chart_slide(prs, "Sensitivity Tornado", fig_sensitivity_tornado, "Tornado chart showing each parameter's impact on ending backlog.")

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
