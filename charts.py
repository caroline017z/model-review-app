"""
38DN Pricing Model Review — Chart Builders
Plotly charts for waterfall, value drivers, and delta comparisons.
"""
import math
import pandas as pd
import plotly.graph_objects as go

from config import P, CHART_COLORS
from utils import safe_float, styled_plotly


def build_capex_waterfall(proj_data, proj_name):
    components = [("EPC", 118), ("LNTP", 119), ("Cust Acq", 121), ("IX Cost", 122), ("Other CapEx", 124)]
    labels, values = [], []
    for lbl, row in components:
        v = safe_float(proj_data.get(row))
        if v is not None and v != 0:
            labels.append(lbl)
            values.append(v)
    if not values:
        return None
    labels.append("Total")
    values.append(sum(values))
    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=["relative"] * (len(values) - 1) + ["total"],
        connector={"line": {"color": "#d0d4dc", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": P["green"]}},
        totals={"marker": {"color": P["navy"]}},
        text=[f"${v:.3f}" for v in values], textposition="outside",
        textfont=dict(family="Century Gothic, DM Sans", size=11, color=P["text"]),
    ))
    fig.update_layout(
        title=dict(text=f"<b>CapEx Build-Up</b>  <span style='font-size:11px;color:#518484'>{proj_name}</span>",
                   font=dict(size=13, color=P["navy"])),
        yaxis_title="$/W", showlegend=False,
        xaxis=dict(tickfont=dict(size=11)),
    )
    return styled_plotly(fig, 380)


def build_value_driver_chart(proj_data, proj_name):
    items = [("NPP", 38), ("FMV", 33), ("EPC Cost", 118), ("IX Cost", 122),
             ("LNTP", 119), ("Upfront Incentive", 216)]
    cmap = {"NPP": P["navy"], "FMV": P["dark_blue"], "EPC Cost": P["blue"],
            "IX Cost": P["teal"], "LNTP": P["cyan"], "Upfront Incentive": P["green"]}
    labels, values, colors = [], [], []
    for lbl, row in items:
        v = safe_float(proj_data.get(row))
        if v is not None and v != 0:
            labels.append(lbl)
            values.append(v)
            colors.append(cmap.get(lbl, P["text"]))
    if not values:
        return None
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=colors,
        text=[f"${v:.3f}/W" if abs(v) < 100 else f"${v:,.0f}" for v in values],
        textposition="outside",
        textfont=dict(family="Century Gothic, DM Sans", size=11, color=P["text"]),
        marker_line=dict(width=0),
    ))
    fig.update_layout(
        title=dict(text=f"<b>Value Drivers</b>  <span style='font-size:11px;color:#518484'>{proj_name}</span>",
                   font=dict(size=13, color=P["navy"])),
        xaxis_title="$/W",
        yaxis=dict(tickfont=dict(size=11)),
    )
    return styled_plotly(fig, 320)


def build_delta_chart(delta_bars, m1_label, m2_label):
    """Horizontal diverging bar chart for input deltas."""
    if not delta_bars:
        return None
    clean = [b for b in delta_bars
             if b.get("Delta") is not None and not (isinstance(b["Delta"], float) and math.isnan(b["Delta"]))]
    if not clean:
        return None
    df_db = pd.DataFrame(clean)
    colors = [P["red"] if v < 0 else P["green"] for v in df_db["Delta"]]
    fig = go.Figure(go.Bar(
        x=df_db["Delta"], y=df_db["Field"], orientation="h",
        marker_color=colors, marker_line=dict(width=0),
        text=[f"({abs(v):.4f})" if v < 0 else f"+{v:.4f}" for v in df_db["Delta"]],
        textposition="outside",
        textfont=dict(family="Century Gothic", size=10,
                      color=[P["red"] if v < 0 else P["green"] for v in df_db["Delta"]]),
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(5,13,37,0.2)")
    fig.update_layout(
        title=dict(text=f"<b>Key Input Deltas</b>  <span style='font-size:10px;color:#518484'>{m2_label} vs {m1_label}</span>",
                   font=dict(size=12, color=P["navy"])),
        xaxis_title="Delta", showlegend=False,
        yaxis=dict(tickfont=dict(family="Century Gothic", size=10), autorange="reversed"),
        xaxis=dict(tickfont=dict(family="Century Gothic", size=10)),
        bargap=0.25,
    )
    return styled_plotly(fig, max(260, len(clean) * 30))


def build_sensitivity_tornado(proj_data, proj_name):
    """Tornado chart showing NPP sensitivity to ±10% changes in key inputs."""
    # Key inputs: (label, row, side)
    # side: "cost" means higher value reduces NPP; "revenue" means higher value increases NPP
    inputs = [
        ("EPC Cost",          118, "cost"),
        ("PPA Rate",          157, "revenue"),
        ("Escalator",         158, "revenue"),
        ("ITC Rate",          597, "revenue"),
        ("Upfront Incentive", 216, "revenue"),
        ("IX Cost",           122, "cost"),
        ("Insurance",         296, "cost"),
    ]

    # Reference values
    system_size = safe_float(proj_data.get(8))   # MWdc
    if not system_size or system_size == 0:
        system_size = 1.0  # fallback

    npp_per_w = safe_float(proj_data.get(38))  # NPP $/W
    if npp_per_w is None:
        return None

    # Build sensitivity bars
    bars = []
    for label, row, side in inputs:
        base_val = safe_float(proj_data.get(row))
        if base_val is None or base_val == 0:
            continue
        delta_input = abs(base_val) * 0.10  # 10% of input

        if side == "cost":
            # For cost inputs ($/W): +10% cost → NPP drops by delta, -10% cost → NPP rises
            impact = delta_input  # $/W direct impact (approximate)
            # If value is very small (like insurance as % or $/kWh), scale appropriately
            if abs(base_val) < 0.001:
                # Likely a percentage — scale to $/W via system economics
                impact = delta_input * 20  # rough $/W proxy
            high_impact = -impact   # +10% cost → negative NPP change
            low_impact = impact     # -10% cost → positive NPP change
        else:
            # For revenue inputs: +10% → NPP improves
            if row == 597:
                # ITC rate: direct impact on $/W via tax credit value
                # ITC contributes roughly ITC_rate × FMV to value
                fmv = safe_float(proj_data.get(33)) or 0
                impact = 0.10 * base_val * fmv if fmv else delta_input
            elif row in (157, 158):
                # PPA / Escalator: revenue-side, approximate as discounted Y1 impact
                # Use a simple 8x multiplier (rough PV of 25-yr revenue stream per $/W-yr)
                impact = delta_input * 8.0
            else:
                # Upfront incentive: direct $/W
                impact = delta_input
            high_impact = impact    # +10% revenue → positive NPP change
            low_impact = -impact    # -10% revenue → negative NPP change

        bars.append({
            "label": label,
            "base_val": base_val,
            "high_impact": high_impact,   # impact when input goes +10%
            "low_impact": low_impact,      # impact when input goes -10%
            "abs_range": abs(high_impact) + abs(low_impact),
        })

    if not bars:
        return None

    # Sort by absolute range (largest at top for tornado)
    bars.sort(key=lambda b: b["abs_range"])

    labels = [b["label"] for b in bars]
    high_vals = [b["high_impact"] for b in bars]
    low_vals = [b["low_impact"] for b in bars]

    fig = go.Figure()

    # Negative-impact bars (red)
    fig.add_trace(go.Bar(
        y=labels,
        x=[min(h, l) for h, l in zip(high_vals, low_vals)],
        orientation="h",
        name="Negative Impact",
        marker_color=P["red"],
        marker_line=dict(width=0),
        text=[f"${v:.4f}" for v in [min(h, l) for h, l in zip(high_vals, low_vals)]],
        textposition="outside",
        textfont=dict(family="Century Gothic, DM Sans", size=10, color=P["red"]),
    ))

    # Positive-impact bars (green)
    fig.add_trace(go.Bar(
        y=labels,
        x=[max(h, l) for h, l in zip(high_vals, low_vals)],
        orientation="h",
        name="Positive Impact",
        marker_color=P["green"],
        marker_line=dict(width=0),
        text=[f"+${v:.4f}" if v > 0 else f"${v:.4f}" for v in [max(h, l) for h, l in zip(high_vals, low_vals)]],
        textposition="outside",
        textfont=dict(family="Century Gothic, DM Sans", size=10, color=P["green"]),
    ))

    fig.add_vline(x=0, line_width=1.5, line_color="rgba(5,13,37,0.25)")

    fig.update_layout(
        title=dict(
            text=f"<b>Sensitivity Analysis (\u00b110%)</b>  <span style='font-size:11px;color:#518484'>{proj_name}</span>",
            font=dict(size=13, color=P["navy"]),
        ),
        xaxis_title="\u0394 NPP ($/W)",
        barmode="overlay",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10)),
        yaxis=dict(tickfont=dict(family="Century Gothic", size=11)),
        xaxis=dict(tickfont=dict(family="Century Gothic", size=10)),
        bargap=0.25,
    )
    return styled_plotly(fig, max(320, len(bars) * 38))
