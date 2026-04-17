"""
38DN Pricing Model Review — Shared Utilities
"""
import re
from datetime import datetime, date
from lib.config import P, PLOTLY_BG, PLOTLY_GRID, PCT_ROWS, TEXT_ROWS, DATE_ROWS, DPW_ROWS, INT_ROWS


def safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


_WS_RE = re.compile(r"\s+")


def canonicalize_name(s) -> str:
    """Canonical form for name/text equality: collapse whitespace, strip, casefold.

    Used for cross-model project name matching, rate curve project lookup,
    orphan reason detection — anywhere two strings should compare equal
    modulo whitespace and case differences.
    """
    return _WS_RE.sub(" ", str(s or "")).strip().casefold()


def fmt_neg(v, is_pct=False):
    """Format a number with red parentheses for negatives."""
    if v is None:
        return "\u2014"
    if is_pct:
        if v < 0:
            return f'<span style="color:#b83230">({abs(v):.2%})</span>'
        return f"{v:.2%}"
    if v < 0:
        return f'<span style="color:#b83230">({abs(v):.4f})</span>'
    return f"{v:.4f}"


def fmt_dollar_w(v):
    return f"${v:.3f}" if v is not None else "\u2014"


def fmt_date(v):
    """Format a value as MM/DD/YYYY if it's a date/datetime, else return string."""
    if v is None:
        return "\u2014"
    if isinstance(v, (datetime, date)):
        return v.strftime("%m/%d/%Y")
    s = str(v).strip()
    if not s or s.lower() == "none":
        return "\u2014"
    return s


def fmt_row_val(v, row):
    """Format a value based on its row's expected unit type."""
    if v is None:
        return "\u2014"
    # String overrides (e.g. "N/A (Custom)") pass through as-is
    if isinstance(v, str) and row not in TEXT_ROWS and row not in DATE_ROWS:
        s = v.strip()
        if s and s.lower() != "none":
            return s
        return "\u2014"
    if row in DATE_ROWS:
        return fmt_date(v)
    if row in TEXT_ROWS:
        s = str(v).strip()
        return s if s and s.lower() != "none" else "\u2014"
    if row in PCT_ROWS:
        fv = safe_float(v)
        if fv is None:
            return "\u2014"
        return f"{fv:.2%}" if abs(fv) < 1 else f"{fv:.2f}%"
    if row in DPW_ROWS:
        fv = safe_float(v)
        return f"{fv:.3f}" if fv is not None else "\u2014"
    if row in INT_ROWS:
        fv = safe_float(v)
        return f"{fv:,.0f}" if fv is not None else "\u2014"
    fv = safe_float(v)
    if fv is None:
        return "\u2014"
    if abs(fv) > 1000:
        return f"{fv:,.0f}"
    return f"{fv:.4f}"


def kpi_card(label, value, sub="", style="accent"):
    return (f'<div class="kpi-card {style}">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')


def styled_plotly(fig, height=360):
    fig.update_layout(
        plot_bgcolor=PLOTLY_BG, paper_bgcolor=PLOTLY_BG,
        font=dict(family="Century Gothic, Segoe UI, sans-serif", color=P["navy"], size=11),
        height=height, margin=dict(t=40, b=28, l=48, r=16),
        xaxis=dict(gridcolor=PLOTLY_GRID, zerolinecolor="rgba(5,13,37,0.12)",
                   tickfont=dict(family="Century Gothic", color=P["navy2"], size=10)),
        yaxis=dict(gridcolor=PLOTLY_GRID, zerolinecolor="rgba(5,13,37,0.12)",
                   tickfont=dict(family="Century Gothic", color=P["navy2"], size=10)),
    )
    return fig


def fmt_val(v, is_pct=False):
    """Generic value formatter for comparison tables."""
    if v is None:
        return "\u2014"
    if is_pct:
        return f"{v:.2%}" if abs(v) < 1 else f"{v:.2f}%"
    if abs(v) > 1000:
        return f"{v:,.0f}"
    return f"{v:.4f}"


def fmt_delta(d, is_pct=False, pct_fmt=False):
    """Format delta with parentheses for negatives."""
    if d is None:
        return "\u2014"
    if pct_fmt:
        return f"({abs(d):.2%})" if d < 0 else f"{d:.2%}"
    if d < 0:
        if is_pct:
            return f"({abs(d):.2%})"
        if abs(d) > 1000:
            return f"({abs(d):,.0f})"
        return f"({abs(d):.4f})"
    if is_pct:
        return f"{d:.2%}"
    if abs(d) > 1000:
        return f"{d:,.0f}"
    return f"{d:.4f}"


# Styling functions for dataframes
def style_field_header(val):
    return "font-weight: 700; color: #050D25"


def style_delta(val):
    if isinstance(val, str) and val.startswith("("):
        return "color: #b83230; font-weight: 600; font-style: italic"
    return "font-style: italic"


def style_flag(v):
    if isinstance(v, (int, float)) and v > 0:
        return "background-color:rgba(184,50,48,0.06);color:#b83230;font-weight:600"
    return ""


def style_warn(v):
    if isinstance(v, (int, float)) and v > 0:
        return "background-color:rgba(69,167,80,0.08);color:#3a7d44;font-weight:600"
    return ""


def style_status(val):
    return {
        "OK": "background-color:rgba(69,167,80,0.08);color:#3a7d44",
        "LOW": "background-color:rgba(184,50,48,0.06);color:#b83230",
        "HIGH": "background-color:rgba(184,50,48,0.06);color:#b83230",
        "WARNING": "background-color:rgba(69,167,80,0.08);color:#3a7d44",
    }.get(val, "")
