"""Translate real pricing-model project data into the VP Review mockup's
JS schema, inject it into the HTML template, and return a string ready for
st.components.v1.html.

Template contract: VP_Review_Mockup.html contains the block

    /* __INJECT_DATA_START__ ... */
    let PORTFOLIO = {...};
    let PROJECTS = [...];
    /* __INJECT_DATA_END__ */

Everything between those markers is replaced at render time.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bible_audit import audit_project

logger = logging.getLogger(__name__)
from bible_reference import CS_AVERAGE, CS_STATE_OVERRIDES, lookup_market
from rows import (
    ROW_PROJECT_NUMBER, ROW_DEVELOPER, ROW_DC_MW, ROW_AC_KW, ROW_STATE, ROW_UTILITY,
    ROW_PROGRAM_A, ROW_PROGRAM_B, ROW_EPC_WRAPPED, ROW_LNTP, ROW_IX,
    ROW_CLOSING, ROW_PPA_RATE, ROW_ESCALATOR, ROW_NPP, ROW_FMV_IRR, ROW_FMV_PER_W,
    ROW_UPFRONT, ROW_INSURANCE, ROW_ITC_PCT, ROW_ELIG_COSTS,
    ROW_OM_PREV, ROW_OM_CORR, ROW_AM_FEE,
    ROW_APPRAISAL_IRR, ROW_LEVERED_PT_IRR, ROW_ACTIVE_MFV,
    ROW_CUSTOM_PROPTAX_TOGGLE, ROW_PROPERTY_TAX_YR1, ROW_PROPTAX_ESCALATOR,
)


def _col_letter(col_idx: int) -> str:
    """Excel-style column letter from a 1-based column index."""
    s = ""
    n = int(col_idx)
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

_TEMPLATE_PATH = Path(__file__).parent / "VP_Review_Mockup.html"
_INJECT_RE = re.compile(
    r"/\* __INJECT_DATA_START__[\s\S]*?__INJECT_DATA_END__ \*/",
    re.MULTILINE,
)

# Row constants now sourced from rows.py. Heatmap references a couple of
# extra rows that don't need top-level aliases here.
HEATMAP_ROW_OM_PREV = ROW_OM_PREV
HEATMAP_ROW_OM_CORR = ROW_OM_CORR
HEATMAP_ROW_AM_FEE = ROW_AM_FEE

# Rule-of-thumb: 1 cent/W swing in sponsor proceeds ≈ 0.18% FMV IRR, calibrated
# at CALIBRATION_SPONSOR_FRACTION (45% sponsor equity). _roll_up rescales
# linearly for other leverage profiles (clamped to [0.5×, 2.0×]). Ships to JS
# via PORTFOLIO.constants.irrPctPerCent so the override recompute path stays
# in sync.
IRR_PCT_PER_CENT = 0.18
# NPV dampener for multi-year OpEx deltas (rough 7% WACC, 25-yr).
OPEX_NPV_FACTOR = 0.55
OPEX_TERM_YEARS = 25

# Assumptions for derived chart data (when real model run isn't available).
DEFAULT_YIELD_KWH_PER_WP = 1.55     # CS average
DEFAULT_DEGRADATION = 0.005         # 0.5% / yr
DEFAULT_OPEX_ESC = 0.02
DEFAULT_OM_PREV = 4_750             # $/MW/yr
DEFAULT_OM_CORR = 2_000
DEFAULT_AM_FEE = 3_000
DEFAULT_INSURANCE = 3_500
TAX_EQUITY_MONETIZATION = 0.85      # TE pays ~85¢ per $1 of ITC
DEBT_FRACTION_OF_NET = 0.55         # DSCR-sized illustrative
CORPORATE_TAX_RATE = 0.21
# MACRS 5-yr (half-year convention) with ITC basis reduction applied separately.
MACRS_5YR = (0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576)
# Bible defaults for the "bible-aligned" capital-stack comparison.
BIBLE_EPC_PER_W = 1.65
BIBLE_LNTP_PER_W = 0.10
BIBLE_CL_PER_W = 0.06
BIBLE_IX_PER_W = 0.05
BIBLE_ITC_FRAC = 0.40
BIBLE_ELIG_FRAC = 0.97
# Terminal-value assumptions (year-25 → year-35 merchant tail).
PANEL_USEFUL_LIFE_YEARS = 35
MERCHANT_RATE_PER_MWH = 25.0        # Post-PPA merchant revenue — conservative
MERCHANT_OPEX_MARGIN = 0.50         # Half of merchant revenue survives OpEx
# IRR calibration: the 0.18% / cent rule assumes ~45% sponsor equity. Scale to
# the project's actual equity fraction to stay stable under high leverage.
CALIBRATION_SPONSOR_FRACTION = 0.45


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("$", "").replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


# Threshold for deciding if a value is stored as fraction (0.40) or whole % (40).
# Values with abs <= this are treated as fractions and scaled ×100 for display.
_PCT_THRESHOLD = 1.5


def _pct_display(n: float | None) -> float | None:
    """Normalize a percentage value for display: fraction → whole number."""
    if n is None:
        return None
    return n * 100 if abs(n) <= _PCT_THRESHOLD else n


def _pct(v: Any) -> str:
    n = _num(v)
    if n is None:
        return "—"
    display = _pct_display(n)
    return f"{display:.0f}%"


def _money_per_w(v: Any) -> str:
    n = _num(v)
    if n is None:
        return "—"
    return f"${n:.2f}"


def _short(label: str, max_len: int = 14) -> str:
    if not label:
        return ""
    s = str(label).split("(")[0].strip()
    return s[:max_len]


def _format_cell(v: Any, unit: str = "") -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, (int, float)):
        if unit == "%":
            display = _pct_display(v)
            return f"{display:.2f}%"
        if unit == "$":
            return f"${v:,.2f}"
        if unit in ("$/W", "$/Wp"):
            return f"${v:.3f}/W"
        if unit == "$/kWh":
            return f"${v:.4f}/kWh"
        if unit == "$/MWh":
            return f"${v:.2f}/MWh"
        if unit == "$/kW-yr":
            return f"${v:,.0f}/kW-yr"
        return f"{v:,.3f}" if abs(v) < 10 else f"{v:,.0f}"
    return str(v)


def _as_fraction(v: Any) -> float | None:
    """Treat 0.4 and 40 both as 40% → 0.4 fraction."""
    n = _num(v)
    if n is None:
        return None
    return n if abs(n) <= _PCT_THRESHOLD else n / 100.0


def _compute_impact(info: dict, data: dict) -> float | None:
    """Rough dollar impact of a single finding on sponsor proceeds.

    Positive = upside vs bible. Negative = hit vs bible.
    """
    exp = _num(info.get("expected"))
    act = _num(info.get("actual"))
    if exp is None or act is None:
        return None
    unit = (info.get("unit") or "").strip()
    label = (info.get("label") or "").lower()
    delta = act - exp
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    if dc_mw <= 0:
        return None
    dc_w = dc_mw * 1_000_000

    if unit == "$/W":
        # Revenue lines (upfront incentive): higher actual = upside
        if "upfront" in label or "incentive" in label:
            return delta * dc_w
        # Cost lines (EPC/LNTP/C&L/IX): higher actual = downside → flip sign
        return -delta * dc_w

    if unit in ("%", "ratio"):
        # Anchor ITC / Eligible-Cost impacts to the BIBLE EPC, not the model's.
        # Otherwise an EPC OFF finding is double-counted through these rows —
        # the EPC delta is already scored by its own finding, so coupling it
        # to tax-credit math inflates _roll_up's total.
        if "itc" in label or "tax credit" in label:
            elig = _as_fraction(data.get(ROW_ELIG_COSTS))
            if elig is None:
                elig = BIBLE_ELIG_FRAC
            exp_f = _as_fraction(exp)
            act_f = _as_fraction(act)
            if exp_f is None or act_f is None:
                return None
            return (act_f - exp_f) * elig * BIBLE_EPC_PER_W * dc_w
        if "eligible" in label:
            itc = _as_fraction(data.get(ROW_ITC_PCT))
            if itc is None:
                itc = BIBLE_ITC_FRAC
            exp_f = _as_fraction(exp)
            act_f = _as_fraction(act)
            if exp_f is None or act_f is None:
                return None
            return (act_f - exp_f) * itc * BIBLE_EPC_PER_W * dc_w
        return None

    if unit in ("$/MW/yr", "$/MW-dc/yr"):
        # OpEx: higher actual = downside → flip sign, amortize over term with NPV dampener
        return -delta * dc_mw * OPEX_TERM_YEARS * OPEX_NPV_FACTOR

    if unit == "$/kWh":
        # Rate-level OpEx (cust mgmt). Approximate annual MWh at 1,550 kWh/Wp × DC_MW.
        annual_mwh = dc_mw * 1_550
        return -delta * annual_mwh * OPEX_TERM_YEARS * OPEX_NPV_FACTOR

    return None


def _roll_up(findings: list[dict], dc_mw: float, sponsor_fraction: float | None = None) -> dict:
    """Aggregate per-finding dollar impacts into headline sponsor metrics.

    sponsor_fraction: the project's equity-to-total-sources ratio; the IRR
    rule-of-thumb (0.18% / cent NPP) is calibrated at ~45% sponsor equity,
    so we rescale linearly for other leverage profiles. Clamped to a
    [0.5×, 2.0×] window to keep thin-equity projects from producing
    ridiculous IRR deltas.
    """
    total = 0.0
    for f in findings:
        v = f.get("impact")
        if isinstance(v, (int, float)):
            total += v
    if dc_mw > 0:
        npp_per_w = total / (dc_mw * 1_000_000)
    else:
        npp_per_w = 0.0

    leverage_scale = 1.0
    if sponsor_fraction and sponsor_fraction > 0:
        leverage_scale = CALIBRATION_SPONSOR_FRACTION / sponsor_fraction
        leverage_scale = max(0.5, min(2.0, leverage_scale))
    irr_pct = (npp_per_w / 0.01) * IRR_PCT_PER_CENT * leverage_scale

    return {
        "nppPerW": round(npp_per_w, 3),
        "irrPct": round(irr_pct, 2),
        "equityK": int(round(total / 1000)),
        "leverageScale": round(leverage_scale, 2),
    }


def _fmt_money_short(v: float) -> str:
    a = abs(v)
    sign = "(" if v < 0 else ""
    close = ")" if v < 0 else ""
    if a >= 1_000_000:
        return f"{sign}${a/1_000_000:.2f}M{close}"
    if a >= 1_000:
        return f"{sign}${a/1_000:.0f}k{close}"
    return f"{sign}${a:.0f}{close}"


def _build_references(proj: dict, audit: dict) -> dict:
    """Per-project bible/market/opex reference lookup."""
    data = proj.get("data", {})
    state = str(audit.get("state") or data.get(ROW_STATE) or "").strip().upper()
    utility = str(data.get(ROW_UTILITY) or "").strip()
    program = str(audit.get("program_used") or data.get(ROW_PROGRAM_A) or data.get(ROW_PROGRAM_B) or "").strip()

    # Bible (cross-market + per-state overrides, e.g. IL hail insurance)
    cs = {**CS_AVERAGE, **CS_STATE_OVERRIDES.get(state, {})}

    def _cs_item(row: int, pretty: str) -> dict | None:
        info = cs.get(row)
        if not info:
            return None
        return {
            "k": pretty,
            "v": _format_cell(info.get("value"), info.get("unit", "")),
            "s": _build_tol_note(info),
        }

    bible_items = [_cs_item(r, p) for r, p in [
        (ROW_EPC_WRAPPED, "EPC ($/W)"),
        (ROW_LNTP, "LNTP ($/W)"),
        (ROW_CLOSING, "Closing & Legal ($/W)"),
        (ROW_ITC_PCT, "ITC Rate"),
        (ROW_ELIG_COSTS, "Eligible Costs %"),
    ]]
    bible_items = [x for x in bible_items if x]

    # Market
    market = lookup_market(state, utility, program)
    market_items: list[dict] = []
    market_header = f"Market — {state} {utility} {program}".strip()
    if market:
        up_val = market.get(ROW_UPFRONT)
        if up_val is not None:
            lag = market.get(217)
            lag_str = f"{int(lag)}-mo lag" if isinstance(lag, (int, float)) and lag else ""
            incentive_detail = market.get("incentive_detail") or ""
            sub = lag_str if not incentive_detail else (incentive_detail + (f" · {lag_str}" if lag_str else ""))
            market_items.append({"k": "Upfront Incentive ($/W)", "v": _format_cell(up_val, "$/W"), "s": sub})
        rec_rate = market.get("rec_rate")
        rec_term = market.get("rec_term")
        if rec_rate is not None:
            rec_v = f"${rec_rate:,.2f}/MWh" if isinstance(rec_rate, (int, float)) else str(rec_rate)
            rec_s = f"{int(rec_term)}-yr" if isinstance(rec_term, (int, float)) else (str(rec_term) if rec_term else "")
            market_items.append({"k": "REC Rate", "v": rec_v, "s": rec_s})
        if market.get("post_rec_rate") not in (None, 0):
            prr = market.get("post_rec_rate"); prt = market.get("post_rec_term")
            market_items.append({
                "k": "Post-REC Rate",
                "v": f"${prr:,.2f}/MWh" if isinstance(prr, (int, float)) else str(prr),
                "s": f"{int(prt)}-yr" if isinstance(prt, (int, float)) else (str(prt) if prt else ""),
            })
        if market.get("rate_curve"):
            market_items.append({
                "k": "Rate Curve",
                "v": str(market["rate_curve"]),
                "s": str(market.get("rate_source") or ""),
            })
        rc_discount = market.get(161)
        if rc_discount not in (None, 0):
            market_items.append({
                "k": "Customer Discount",
                "v": f"{rc_discount*100:.1f}%" if isinstance(rc_discount, (int, float)) else str(rc_discount),
                "s": "Applied to rate curve",
            })

    # OpEx
    opex_items = []
    ins = _cs_item(ROW_INSURANCE, "Insurance ($/MW-yr)")
    if ins:
        opex_items.append(ins)
    if market and 240 in market and market[240] not in (None, 0):
        opex_items.append({
            "k": "Cust Mgmt ($/kWh)",
            "v": f"${market[240]:.4f}/kWh",
            "s": "Market-specific",
        })
    if market and market.get("cust_acq_blend") is not None:
        opex_items.append({
            "k": "Cust Acquisition (blended)",
            "v": f"${market['cust_acq_blend']:.4f}/kWh",
            "s": str(market.get("cust_mix") or ""),
        })

    return {
        "bibleHeader": f"Q1 '26 Bible · {state} {utility} {program}".strip(),
        "bible": bible_items,
        "marketHeader": market_header if market else f"Market — (no match for {state}/{utility}/{program})",
        "market": market_items,
        "marketMatched": bool(market),
        "opex": opex_items,
    }


def _build_tol_note(info: dict) -> str:
    tol = info.get("tol")
    unit = info.get("unit", "")
    if not tol:
        return "Exact match" if info.get("tol") == 0 else ""
    if unit == "$/W":
        return f"Tol ±${tol:.3f}"
    if unit in ("%", "ratio"):
        t = tol * 100 if abs(tol) <= 1 else tol
        return f"Tol ±{t:.1f}%"
    if unit in ("$/MW/yr", "$/MW-dc/yr"):
        return f"Tol ±${tol:,.0f}"
    return f"Tol ±{tol}"


def _verdict_from_summary(summary: dict[str, int]) -> str:
    off = summary.get("OFF", 0)
    out = summary.get("OUT", 0)
    missing = summary.get("MISSING", 0)
    if off == 0 and out == 0 and missing == 0:
        return "CLEAN"
    if off >= 2 or (off >= 1 and out >= 2):
        return "REWORK REQUIRED"
    return "REVIEW"


def _derive_sub(proj: dict, audit: dict, label: str) -> str:
    data = proj.get("data", {})
    state = (audit.get("state") or data.get(ROW_STATE) or "").strip() if isinstance(data.get(ROW_STATE), str) else (audit.get("state") or "")
    utility = (data.get(ROW_UTILITY) or "").strip() if isinstance(data.get(ROW_UTILITY), str) else ""
    program = audit.get("program_used") or data.get(ROW_PROGRAM_A) or data.get(ROW_PROGRAM_B) or ""
    if isinstance(program, str):
        program = program.strip()
    parts = [label] if label else []
    loc_parts = [p for p in [state, utility] if p]
    if loc_parts:
        parts.append(" ".join(loc_parts))
    if program:
        parts.append(str(program))
    return " · ".join(parts)


def _build_findings(audit: dict, data: dict) -> list[dict]:
    findings: list[dict] = []
    for row_num, info in audit.get("rows", {}).items():
        status = info.get("status", "OK")
        if status == "OK":
            continue
        unit = info.get("unit", "") or ""
        field_label = info.get("label") or f"Row {row_num}"
        bible_str = _format_cell(info.get("expected"), unit)
        model_str = _format_cell(info.get("actual"), unit)
        exp_n = _num(info.get("expected"))
        act_n = _num(info.get("actual"))
        delta_n = None
        if exp_n is not None and act_n is not None:
            delta_n = round(act_n - exp_n, 4)
        impact = _compute_impact(info, data)
        findings.append({
            "field": str(field_label),
            "short": _short(str(field_label)),
            "bible": bible_str,
            "model": model_str,
            "delta": delta_n,
            "deltaUnit": unit,
            "impact": round(impact) if isinstance(impact, (int, float)) else None,
            "status": status,
            "source": info.get("source", ""),
        })
    for gh in audit.get("guidehouse", []) or []:
        status = gh.get("status", "OK")
        if status == "OK":
            continue
        exp = gh.get("expected")
        act = gh.get("actual")
        findings.append({
            "field": f"RC{gh.get('rate_idx', '?')} discount ({gh.get('name', '')})",
            "short": f"RC{gh.get('rate_idx', '?')}",
            "bible": f"{exp*100:.2f}%" if isinstance(exp, (int, float)) else "—",
            "model": f"{act*100:.2f}%" if isinstance(act, (int, float)) else "—",
            "delta": None,
            "deltaUnit": "%",
            "impact": None,
            "status": status,
            "source": "Guidehouse strip",
        })
    return findings


def _build_variance(findings: list[dict]) -> dict:
    """Variance chart: sort by $-impact magnitude, show top 6 in $k."""
    scored = [f for f in findings if isinstance(f.get("impact"), (int, float))]
    unscored = [f for f in findings if not isinstance(f.get("impact"), (int, float))]
    scored.sort(key=lambda f: -abs(f["impact"]))
    sliced = scored[:6]
    if not sliced and not unscored:
        return {"labels": ["No findings"], "x": [0], "txt": ["—"], "colors": ["miss"]}
    if not sliced:
        # Fall back to severity view for unscored findings (e.g. MISSING, sentinel)
        order = {"OFF": 0, "OUT": 1, "REVIEW": 2, "MISSING": 3}
        unscored.sort(key=lambda f: order.get(f["status"], 9))
        labels, xs, txts, colors = [], [], [], []
        for f in unscored[:6]:
            labels.append(f.get("short") or f["field"][:20])
            xs.append(0)
            txts.append(f["status"])
            c = {"OFF": "off", "OUT": "out"}.get(f["status"], "miss")
            colors.append(c)
        return {"labels": labels, "x": xs, "txt": txts, "colors": colors}
    labels, xs, txts, colors = [], [], [], []
    color_map = {"OFF": "off", "OUT": "out", "REVIEW": "miss", "MISSING": "miss"}
    for f in sliced:
        labels.append(f.get("short") or f["field"][:20])
        xs.append(round(f["impact"] / 1000, 1))  # $k
        txts.append(_fmt_money_short(f["impact"]))
        colors.append(color_map.get(f["status"], "miss"))
    return {"labels": labels, "x": xs, "txt": txts, "colors": colors}


def _build_kpis(proj: dict, findings: list[dict]) -> dict:
    data = proj.get("data", {})
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    ac_kw = _num(data.get(ROW_AC_KW)) or 0
    ac_mw = ac_kw / 1000 if ac_kw else 0
    epc = _num(data.get(ROW_EPC_WRAPPED))
    npp = _num(data.get(ROW_NPP))
    npp_dollars = _num(data.get(39))   # NPP ($) — for the 'Total $X.XM' subline
    fmv_per_w = _num(data.get(ROW_FMV_PER_W))
    itc = _num(data.get(ROW_ITC_PCT))
    appraisal_irr = _num(data.get(ROW_APPRAISAL_IRR))   # row 31
    levered_pt_irr = _num(data.get(ROW_LEVERED_PT_IRR))  # row 37
    active_mfv = _num(data.get(ROW_ACTIVE_MFV))          # row 681
    epc_off = any(f["status"] == "OFF" and "EPC" in f["field"].upper() for f in findings)
    itc_off = any(f["status"] == "OFF" and "ITC" in f["field"].upper() for f in findings)

    # Appraisal IRR (row 31) is stored as a fraction (0.0725). Display as %.
    irr_display = None
    if appraisal_irr is not None:
        irr_display = f"{_pct_display(appraisal_irr):.2f}%"

    # Levered Pre-Tax IRR (row 37)
    lev_irr_display = None
    if levered_pt_irr is not None:
        lev_irr_display = f"{_pct_display(levered_pt_irr):.2f}%"

    # ITC: if the model doesn't expose ITC Rate as an input row (common —
    # tax assumptions sit on a different sheet), fall back to the bible
    # default with a small note rather than showing '—'.
    itc_sub = ""
    itc_display = None
    if itc is not None:
        itc_display = f"{_pct_display(itc):.0f}%"
    else:
        itc_display = f"{int(BIBLE_ITC_FRAC*100)}%"
        itc_sub = "bible default"

    # NPP sub-label shows the dollar total when present.
    npp_sub = ""
    if npp_dollars is not None and abs(npp_dollars) >= 1000:
        npp_sub = _fmt_money_short(npp_dollars) + " total"

    # Appraisal IRR sub-label: show FMV $/W + Levered PT IRR when available.
    irr_sub_parts = []
    if fmv_per_w is not None:
        irr_sub_parts.append(f"FMV ${fmv_per_w:.2f}/W")
    if lev_irr_display:
        irr_sub_parts.append(f"Lev PT {lev_irr_display}")
    irr_sub = " · ".join(irr_sub_parts)

    return {
        "dc": f"{dc_mw:.2f}" if dc_mw else "—",
        "dcSub": f"{ac_mw:.2f} MW AC" if ac_mw else "",
        "epc": _money_per_w(epc),
        "epcSub": "",
        "epcOff": bool(epc_off),
        "npp": _money_per_w(npp),
        "nppSub": npp_sub,
        "itc": itc_display or "—",
        "itcSub": itc_sub,
        "itcOff": bool(itc_off),
        "irr": irr_display or "—",
        "irrSub": irr_sub,
        "irrLabel": "Appraisal IRR",
        "levIrr": lev_irr_display or "—",
        "activeMfv": f"${active_mfv:,.0f}" if active_mfv is not None else "—",
    }


def _build_wrapped_epc(audit: dict) -> list[dict]:
    comps = (audit.get("wrapped_epc") or {}).get("components") or []
    out = []
    for c in comps:
        val = _num(c.get("value"))
        if val is None:
            continue
        out.append({"label": str(c.get("component", "")), "value": round(val, 3)})
    return out


def _build_capital_stack(proj: dict, market: dict | None) -> dict:
    """Four-bar capital stack ($/W) for Model vs Bible-aligned.

    Order: Sponsor Equity, Tax Equity, Debt, Incentives.
    """
    data = proj.get("data", {})
    def _fill(val, fallback):
        return val if val is not None else fallback

    epc = _fill(_num(data.get(ROW_EPC_WRAPPED)), BIBLE_EPC_PER_W)
    lntp = _fill(_num(data.get(ROW_LNTP)), BIBLE_LNTP_PER_W)
    cl = _fill(_num(data.get(ROW_CLOSING)), BIBLE_CL_PER_W)
    ix = _fill(_num(data.get(ROW_IX)), BIBLE_IX_PER_W)
    upfront = _fill(_num(data.get(ROW_UPFRONT)), 0.0)
    # Explicit 0 must stay 0 — can't use `or` fallback on ITC/eligible.
    itc = _fill(_as_fraction(data.get(ROW_ITC_PCT)), BIBLE_ITC_FRAC)
    elig = _fill(_as_fraction(data.get(ROW_ELIG_COSTS)), BIBLE_ELIG_FRAC)

    model_total = epc + lntp + cl + ix
    te_value = itc * elig * model_total * TAX_EQUITY_MONETIZATION
    model_net = max(0.0, model_total - upfront - te_value)
    model_debt = model_net * DEBT_FRACTION_OF_NET
    model_sponsor = model_net - model_debt

    bible_upfront = 0.0
    if market and isinstance(market.get(ROW_UPFRONT), (int, float)):
        bible_upfront = float(market[ROW_UPFRONT])
    bible_total = BIBLE_EPC_PER_W + BIBLE_LNTP_PER_W + BIBLE_CL_PER_W + BIBLE_IX_PER_W
    bible_te = BIBLE_ITC_FRAC * BIBLE_ELIG_FRAC * bible_total * TAX_EQUITY_MONETIZATION
    bible_net = max(0.0, bible_total - bible_upfront - bible_te)
    bible_debt = bible_net * DEBT_FRACTION_OF_NET
    bible_sponsor = bible_net - bible_debt

    def _nn(x: float) -> float:
        return round(max(0.0, float(x)), 3)

    # Flag whether we detected a real DSCR schedule — hints that the
    # illustrative 55/45 debt split could be tightened in a future iteration.
    dscr_schedule = proj.get("dscr_schedule") or {}
    has_dscr = bool(dscr_schedule) and any(
        isinstance(v, (int, float)) and v > 0 for v in dscr_schedule.values()
    )
    return {
        "model": [_nn(model_sponsor), _nn(te_value), _nn(model_debt), _nn(upfront)],
        "bible": [_nn(bible_sponsor), _nn(bible_te), _nn(bible_debt), _nn(bible_upfront)],
        "illustrative": True,
        "assumptions": {
            "debtFraction": DEBT_FRACTION_OF_NET,
            "teMonetization": TAX_EQUITY_MONETIZATION,
            "hasModelDscr": has_dscr,
        },
    }


def _primary_rate(proj: dict) -> tuple[float | None, float | None]:
    """Return (rate_per_kwh, escalator_frac) from the first live rate component.

    Models vary — PPA rate and escalator don't always sit at fixed rows on
    Project Inputs. The rate-component block (already parsed by data_loader)
    is the authoritative source. We pick the first component with a positive
    energy_rate and an equity_on toggle; fall back to the first with a rate.
    """
    comps = proj.get("rate_comps") or {}
    best = None
    for idx in sorted(comps):
        c = comps[idx] or {}
        rate = _num(c.get("energy_rate"))
        if rate is None or rate <= 0:
            continue
        esc_raw = c.get("escalator")
        # "N/A (Custom)" sentinel should be treated as 0 escalator.
        esc = _num(esc_raw) if not (isinstance(esc_raw, str) and "custom" in esc_raw.lower()) else 0.0
        # Prefer components that fund equity distributions.
        if c.get("equity_on"):
            return rate, esc
        if best is None:
            best = (rate, esc)
    return best if best else (None, None)


def _build_cashflow(proj: dict) -> dict:
    """25-year operating CF / tax benefits / terminal value (in $ thousands).

    Revenue: yield × DC_MW × PPA rate × escalator, with 0.5%/yr degradation.
    Tax benefits: ITC year-1 + MACRS depreciation shield years 1–6.
    Terminal: ~2.5× final-year operating CF.
    """
    data = proj.get("data", {})
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    if dc_mw <= 0:
        zero = [0] * 25
        return {"opCF": zero, "taxBn": zero, "terminal": zero}

    # PPA rate + escalator: canonical rows first, rate-components as fallback
    # (they are the source of truth when Project Inputs labels have drifted).
    ppa_rate = _num(data.get(ROW_PPA_RATE))
    escalator = _num(data.get(ROW_ESCALATOR))
    rc_rate, rc_esc = _primary_rate(proj)
    if ppa_rate is None:
        ppa_rate = rc_rate if rc_rate is not None else 0.08
    if escalator is None:
        escalator = rc_esc if rc_esc is not None else 0.015
    if abs(escalator) > 0.5:
        escalator = escalator / 100.0

    epc = _num(data.get(ROW_EPC_WRAPPED))
    if epc is None:
        epc = BIBLE_EPC_PER_W
    itc_frac = _as_fraction(data.get(ROW_ITC_PCT))
    if itc_frac is None:
        itc_frac = 0.0
    elig_frac = _as_fraction(data.get(ROW_ELIG_COSTS))
    if elig_frac is None:
        elig_frac = BIBLE_ELIG_FRAC

    # In thousands of $: DC_MW × 1000 kW × yield (kWh/Wp) × 1000 = MWh, then × rate = $
    annual_mwh = dc_mw * DEFAULT_YIELD_KWH_PER_WP * 1000
    total_opex_mw_yr = DEFAULT_OM_PREV + DEFAULT_OM_CORR + DEFAULT_AM_FEE + DEFAULT_INSURANCE

    # ITC basis reduction is half the ITC, applied ONLY to the eligible
    # portion of CapEx. Ineligible CapEx still depreciates at full basis.
    # Using itc_frac alone against total CapEx over-reduces the depreciable
    # basis by ~3%, understating tax benefits.
    total_capex_k = epc * dc_mw * 1000
    basis_k = total_capex_k * (1 - itc_frac * elig_frac / 2)
    itc_year1_k = itc_frac * elig_frac * total_capex_k

    op_cf: list[int] = []
    tax_bn: list[int] = []
    terminal: list[int] = []
    for yr_idx in range(OPEX_TERM_YEARS):
        year = yr_idx + 1
        prod_mwh = annual_mwh * ((1 - DEFAULT_DEGRADATION) ** yr_idx)
        # Revenue in $k: (MWh → kWh) × ($/kWh) = $, then ÷ 1000 = $k.
        rev_k = prod_mwh * 1000 * ppa_rate * ((1 + escalator) ** yr_idx) / 1000
        opex_k = dc_mw * total_opex_mw_yr * ((1 + DEFAULT_OPEX_ESC) ** yr_idx) / 1000
        op_cf.append(int(round(rev_k - opex_k)))

        tb = 0.0
        if year == 1:
            tb += itc_year1_k
        if yr_idx < len(MACRS_5YR):
            tb += MACRS_5YR[yr_idx] * basis_k * CORPORATE_TAX_RATE
        tax_bn.append(int(round(tb)))

        # Terminal value in year 25: PV of the year-25→year-35 merchant tail.
        # Replaces the prior 2.5×opCF rule, which overstated TV by 40–70%.
        # Assume the plant continues producing at year-25 degraded output at
        # a conservative merchant rate; OpEx consumes half; discount at the
        # OpEx NPV factor over the remaining useful life.
        if year == OPEX_TERM_YEARS:
            remaining_life = max(0, PANEL_USEFUL_LIFE_YEARS - OPEX_TERM_YEARS)
            merchant_rev_k = (
                prod_mwh * MERCHANT_RATE_PER_MWH * MERCHANT_OPEX_MARGIN / 1000
            )
            terminal.append(int(round(
                merchant_rev_k * remaining_life * OPEX_NPV_FACTOR
            )))
        else:
            terminal.append(0)

    return {"opCF": op_cf, "taxBn": tax_bn, "terminal": terminal}


def _build_sensitivity(proj: dict) -> dict:
    """±10% input shocks translated into ΔNPP $/W via _compute_impact rules.

    Returns {labels, lo, hi} sorted by swing magnitude; truncated to 7 inputs.
    """
    data = proj.get("data", {})
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    dc_w = dc_mw * 1_000_000 if dc_mw > 0 else 0

    candidates: list[dict] = []

    def _add(label: str, delta_dollars_at_plus_10: float):
        """delta_dollars_at_plus_10 = $ impact on sponsor proceeds if input goes +10%.
        Stored as ΔNPP $/W (lo at -10%, hi at +10%)."""
        if not dc_w:
            return
        per_w = delta_dollars_at_plus_10 / dc_w
        candidates.append({"label": label, "lo": -per_w, "hi": per_w})

    epc = _num(data.get(ROW_EPC_WRAPPED))
    if epc:
        # +10% EPC → more cost → negative impact on sponsor.
        _add("EPC $/W", -0.10 * epc * dc_w)

    itc = _as_fraction(data.get(ROW_ITC_PCT))
    elig = _as_fraction(data.get(ROW_ELIG_COSTS)) or BIBLE_ELIG_FRAC
    if itc and epc:
        # +10% of 40% ITC = +4 pp ITC → positive impact.
        _add("ITC %", (itc * 0.10) * elig * epc * dc_w)

    upfront = _num(data.get(ROW_UPFRONT))
    if upfront:
        _add("Upfront Incentive $/W", 0.10 * upfront * dc_w)

    ppa = _num(data.get(ROW_PPA_RATE))
    if ppa:
        annual_mwh = dc_mw * DEFAULT_YIELD_KWH_PER_WP * 1000
        # +10% rate → ΔRevenue/yr × 25-yr × NPV dampener.
        delta_annual = 0.10 * ppa * annual_mwh * 1000
        _add("PPA Rate $/kWh", delta_annual * OPEX_TERM_YEARS * OPEX_NPV_FACTOR)

    lntp = _num(data.get(ROW_LNTP))
    if lntp:
        _add("LNTP $/W", -0.10 * lntp * dc_w)

    # OpEx (use benchmark total × DC_MW)
    if dc_mw:
        total_opex = DEFAULT_OM_PREV + DEFAULT_OM_CORR + DEFAULT_AM_FEE + DEFAULT_INSURANCE
        _add("OpEx $/MW-yr",
             -0.10 * total_opex * dc_mw * OPEX_TERM_YEARS * OPEX_NPV_FACTOR)

    insurance = _num(data.get(ROW_INSURANCE))
    if insurance and dc_mw:
        _add("Insurance $/MW-yr",
             -0.10 * insurance * dc_mw * OPEX_TERM_YEARS * OPEX_NPV_FACTOR)

    # Rank by absolute swing, take top 7
    candidates.sort(key=lambda c: -abs(c["hi"] - c["lo"]))
    candidates = candidates[:7]

    return {
        "labels": [c["label"] for c in candidates],
        "lo": [round(c["lo"], 3) for c in candidates],
        "hi": [round(c["hi"], 3) for c in candidates],
    }


def _build_rate_comp1(proj: dict) -> dict:
    """Extract Rate Component 1 details for display.

    In community solar models, there's no single PPA rate — revenue comes from
    rate components. RC1 is typically the Guidehouse rate with a haircut
    (discount) mentioned in the component name (e.g., "GH25 -22.5%").
    """
    comps = proj.get("rate_comps") or {}
    rc1 = comps.get(1) or {}
    name = str(rc1.get("name") or "").strip()
    rate = _num(rc1.get("energy_rate"))
    esc = rc1.get("escalator")
    discount = _num(rc1.get("discount"))
    equity_on = bool(rc1.get("equity_on"))

    # Try to extract haircut % from the name (e.g., "GH25 -22.5%" → -22.5)
    haircut_pct = None
    if name:
        import re as _rc_re
        m = _rc_re.search(r'[-–]\s*(\d+\.?\d*)\s*%', name)
        if m:
            haircut_pct = float(m.group(1))

    return {
        "name": name or "—",
        "rate": round(rate, 6) if rate is not None else None,
        "rateDisplay": f"${rate:.4f}/kWh" if rate is not None else "—",
        "escalator": str(esc) if esc is not None else "—",
        "discount": round(discount, 4) if discount is not None else None,
        "discountDisplay": f"{discount*100:.1f}%" if discount is not None else "—",
        "haircut": haircut_pct,
        "equityOn": equity_on,
    }


def _build_property_tax(data: dict) -> dict:
    """Extract property tax info. Only meaningful when custom toggle is on."""
    toggle_raw = data.get(ROW_CUSTOM_PROPTAX_TOGGLE)
    # Toggle can be 1/0, "On"/"Off", True/False
    is_custom = False
    if toggle_raw is not None:
        n = _num(toggle_raw)
        if n is not None:
            is_custom = n != 0
        else:
            is_custom = str(toggle_raw).strip().lower() in ("1", "on", "true", "yes", "custom")

    yr1 = _num(data.get(ROW_PROPERTY_TAX_YR1))
    esc = _num(data.get(ROW_PROPTAX_ESCALATOR))

    return {
        "customToggle": is_custom,
        "yr1": round(yr1, 2) if yr1 is not None else None,
        "yr1Display": f"${yr1:,.0f}" if yr1 is not None else "—",
        "escalator": f"{_pct_display(esc):.2f}%" if esc is not None else "—",
    }


def _build_mockup_project(proj: dict, audit: dict, label: str) -> dict:
    data = proj.get("data", {})
    findings = _build_findings(audit, data)
    summary = audit.get("summary", {}) or {}
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    # Look up market once so the capital stack's "bible upfront" is market-aware.
    # (lookup_market itself handles MD/DE normalization; no need to pre-normalize.)
    market = lookup_market(
        str(audit.get("state") or data.get(ROW_STATE) or "").strip(),
        str(data.get(ROW_UTILITY) or "").strip(),
        str(audit.get("program_used") or data.get(ROW_PROGRAM_A) or data.get(ROW_PROGRAM_B) or "").strip(),
    )
    stack = _build_capital_stack(proj, market)
    # Feed sponsor fraction into the roll-up so IRR scales with actual leverage.
    model_total = sum(stack["model"]) or 1.0
    sponsor_fraction = stack["model"][0] / model_total if model_total else None
    rolled = _roll_up(findings, dc_mw, sponsor_fraction=sponsor_fraction)
    developer = str(data.get(ROW_DEVELOPER) or "").strip()
    utility = str(data.get(ROW_UTILITY) or "").strip()
    program = str(
        audit.get("program_used")
        or data.get(ROW_PROGRAM_A)
        or data.get(ROW_PROGRAM_B)
        or ""
    ).strip()
    pnum_raw = data.get(ROW_PROJECT_NUMBER)
    try:
        proj_number = int(pnum_raw) if pnum_raw not in (None, "") else None
    except (TypeError, ValueError):
        proj_number = None
    return {
        "name": proj.get("name") or "Unnamed",
        "sub": _derive_sub(proj, audit, label),
        # First-class fields for the portfolio summary / nav — consumers no
        # longer parse `sub` strings to recover them.
        "projNumber": proj_number,        # Project # from Project Inputs row 2
        "developer": developer,
        "state": audit.get("state") or str(data.get(ROW_STATE) or "").strip(),
        "utility": utility,
        "program": program,
        "verdict": _verdict_from_summary(summary),
        "irrPct": rolled["irrPct"],
        "nppPerW": rolled["nppPerW"],
        "equityK": rolled["equityK"],
        "leverageScale": rolled["leverageScale"],
        "sponsorFraction": round(sponsor_fraction or 0, 3),
        "kpis": _build_kpis(proj, findings),
        "findings": findings,
        "variance": _build_variance(findings),
        "stack": stack,
        "cashflow": _build_cashflow(proj),
        "tornado": _build_sensitivity(proj),
        "wrappedEpcComponents": _build_wrapped_epc(audit),
        "references": _build_references(proj, audit),
        "rateComp1": _build_rate_comp1(proj),
        "propertyTax": _build_property_tax(data),
    }


def _safe_audit(proj_data: dict, proj_name: str = "") -> dict:
    try:
        return audit_project(proj_data)
    except Exception as exc:  # noqa: BLE001 — we want to surface any audit failure
        logger.exception("audit_project failed for project %r: %s", proj_name, exc)
        return {
            "rows": {},
            "summary": {"OK": 0, "OFF": 0, "OUT": 0, "MISSING": 0, "REVIEW": 0},
            "guidehouse": [],
            "wrapped_epc": {},
            "state": "", "utility": "", "program_used": "",
        }


def _iter_projects(m1_projects: dict):
    """Yield (col, proj_dict) pairs for real projects only."""
    if not m1_projects:
        return
    for k, v in m1_projects.items():
        if not isinstance(v, dict):
            continue
        if isinstance(k, str) and k.startswith("_"):
            continue
        if "data" not in v:
            continue
        yield k, v


import re as _re  # local alias to avoid shadowing


# Template-placeholder detection. Real model templates ship with ~60 scratch
# slots named "Project 15" / "Project 16" / … with developer literally set to
# "[Developer]" and DC=7.0 — these should never surface, even toggle-off.
_PLACEHOLDER_NAME_RE = _re.compile(r"^\s*project\s+\d+\s*$", _re.IGNORECASE)
_PLACEHOLDER_DEV_TOKENS = {"[developer]", "developer", "tbd", "n/a", "—", "-"}


def _looks_real(proj: dict) -> bool:
    """A project is 'real' if it has a proper name, a positive DC size, AND
    doesn't look like a template placeholder ("Project 15", "[Developer]"…).
    """
    name = str(proj.get("name") or "").strip()
    if not name or name.lower() in ("", "project", "sample"):
        return False
    if _PLACEHOLDER_NAME_RE.match(name):
        return False
    data = proj.get("data", {}) or {}
    dc = _num(data.get(ROW_DC_MW)) or 0
    if dc <= 0:
        return False
    dev = str(data.get(ROW_DEVELOPER) or "").strip().lower()
    if dev in _PLACEHOLDER_DEV_TOKENS:
        return False
    return True


def list_candidate_projects(m1_projects: dict) -> list[dict]:
    """Return every project column that has a real name + DC size.

    Each returned dict carries:
      * id            stable string key for session_state
      * name          project name
      * dc            DC size in MW
      * developer     row-10 developer name (for grouping)
      * state / utility / program
      * toggled_on    whether the model's row-7 toggle is On
      * suggested     True when the project is a default-on suggestion —
                      either toggle=On itself, OR toggle=Off but same
                      developer as at least one toggled-on project
                      (portfolio-sibling rule)

    The sidebar shows `suggested=True` candidates checked by default and
    `suggested=False` under an 'Add off-toggled' expander.
    """
    # First pass: collect raw candidates.
    raw: list[dict] = []
    for col, proj in _iter_projects(m1_projects):
        if not _looks_real(proj):
            continue
        data = proj.get("data", {}) or {}
        # Project # comes from row 2 — used by Returns sheets to label columns.
        # Important when project NAMES collide (e.g. two 'IL Joel' columns):
        # the proj-number disambiguates them.
        pnum_raw = data.get(ROW_PROJECT_NUMBER)
        proj_number = None
        if pnum_raw not in (None, ""):
            # Handle float (1.0), int (1), or string ("1", "Project 1")
            pf = _num(pnum_raw)
            if pf is not None:
                proj_number = int(pf)
            elif isinstance(pnum_raw, str):
                # Extract trailing digits from strings like "Project 1"
                import re as _pnum_re
                m = _pnum_re.search(r'\d+', str(pnum_raw))
                if m:
                    proj_number = int(m.group())
        col_idx = int(col) if isinstance(col, (int, float)) else None
        raw.append({
            "id": str(col),
            "col_letter": _col_letter(col_idx) if col_idx else str(col),
            "proj_number": proj_number,
            "name": str(proj.get("name") or "Unnamed").strip(),
            "dc": round(_num(data.get(ROW_DC_MW)) or 0, 2),
            "developer": str(data.get(ROW_DEVELOPER) or "").strip(),
            "state": str(data.get(ROW_STATE) or "").strip(),
            "utility": str(data.get(ROW_UTILITY) or "").strip(),
            "program": str(data.get(ROW_PROGRAM_A) or data.get(ROW_PROGRAM_B) or "").strip(),
            "toggled_on": bool(proj.get("toggle", False)),
        })

    # Default-suggested = row-7 toggle=On OR same developer as any On project.
    # Duplicate-named columns both count if both carry the same developer.
    # Off-toggled projects whose developer matches an active one are flagged
    # `dev_sibling=True` so the sidebar can distinguish them visually, but
    # they're still included in `suggested` (default-checked).
    active_devs = {
        (c["developer"] or "").lower()
        for c in raw if c["toggled_on"] and (c["developer"] or "").strip()
    }
    for c in raw:
        dev_l = (c["developer"] or "").lower()
        c["dev_sibling"] = bool(
            not c["toggled_on"] and dev_l and dev_l in active_devs
        )
        c["suggested"] = bool(c["toggled_on"] or c["dev_sibling"])
    return raw


def filter_projects(m1_projects: dict, included_ids: set[str] | None) -> dict:
    """Return a new dict containing only the projects whose str(col) is in
    `included_ids`. If `included_ids` is None, returns all candidates
    (toggle=On + real data); callers should pre-filter via list_candidate_projects."""
    candidates = {str(c["id"]) for c in list_candidate_projects(m1_projects)}
    if included_ids is None:
        allowed = candidates
    else:
        allowed = candidates & {str(i) for i in included_ids}
    out = {}
    for col, proj in _iter_projects(m1_projects):
        if str(col) in allowed:
            out[col] = proj
    return out


def _default_json(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    # Preserve Decimal numeric fidelity so JS keeps typeof==='number'.
    try:
        from decimal import Decimal
        if isinstance(o, Decimal):
            return float(o)
    except ImportError:
        pass
    # openpyxl Cell objects have a .value attribute
    if hasattr(o, "value") and not callable(o):
        try:
            return o.value
        except Exception:
            pass
    return str(o)


def _safe_json(payload) -> str:
    """json.dumps hardened for <script> embedding.

    Neutralizes four breakout vectors:
      * </script> and its friends (any </ opener)
      * <!-- HTML comment opener
      * U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR, which terminate
        JS string literals in older runtimes and break the embedded script
    """
    s = json.dumps(payload, default=_default_json, ensure_ascii=False)
    return (
        s.replace("</", "<\\/")
         .replace("<!--", "<\\!--")
         .replace("\u2028", "\\u2028")
         .replace("\u2029", "\\u2029")
    )


# Status → heatmap code (0 OK, 1 OUT, 2 OFF, 3 MISSING/REVIEW).
_STATUS_CODE = {"OK": 0, "OUT": 1, "OFF": 2, "MISSING": 3, "REVIEW": 3}
# (heatmap column label, rows in the audit that flow into that column)
_HEATMAP_COLUMNS = [
    ("EPC",       [ROW_EPC_WRAPPED]),
    ("LNTP",      [ROW_LNTP]),
    ("C&L",       [ROW_CLOSING]),
    ("ITC",       [ROW_ITC_PCT]),
    ("Elig Cost", [ROW_ELIG_COSTS]),
    ("Upfront",   [ROW_UPFRONT]),
    ("Insurance", [ROW_INSURANCE]),
    ("O&M",       [ROW_OM_PREV, ROW_OM_CORR]),
    ("AM Fee",    [ROW_AM_FEE]),
]


def _build_heatmap_row(audit: dict) -> list[int]:
    rows = audit.get("rows") or {}
    out: list[int] = []
    for _, audit_rows in _HEATMAP_COLUMNS:
        worst = 0
        for r in audit_rows:
            status = (rows.get(r) or {}).get("status", "OK")
            code = _STATUS_CODE.get(status, 0)
            if code > worst:
                worst = code
        out.append(worst)
    return out


def build_payload(
    m1_projects: dict,
    *,
    model_label: str = "Model",
    reviewer: str = "Caroline Z.",
    bible_label: str = "Q1 '26",
) -> tuple[list[dict], dict]:
    """Build (projects_list, portfolio_dict) from real model data."""
    projects_list: list[dict] = []
    totals = {"OFF": 0, "OUT": 0, "MISSING": 0, "REVIEW": 0, "OK": 0}
    total_mw = 0.0
    heatmap_z: list[list[int]] = []
    heatmap_projects: list[str] = []

    for _, proj in _iter_projects(m1_projects):
        audit = _safe_audit(proj.get("data", {}), proj.get("name", ""))
        projects_list.append(_build_mockup_project(proj, audit, model_label))
        summary = audit.get("summary", {}) or {}
        for k in totals:
            totals[k] += summary.get(k, 0) or 0
        mw = _num(proj.get("data", {}).get(ROW_DC_MW)) or 0
        total_mw += mw
        heatmap_z.append(_build_heatmap_row(audit))
        heatmap_projects.append(str(proj.get("name") or "Unnamed"))

    portfolio = {
        "off": totals["OFF"],
        "out": totals["OUT"],
        "missing": totals["MISSING"],
        "review": totals["REVIEW"],
        "count": len(projects_list),
        "totalMw": round(total_mw, 1),
        "reviewed": 0,
        "pending": len(projects_list),
        "modelName": model_label or "No model loaded",
        "bibleLabel": bible_label,
        "loadedDate": datetime.now().strftime("%b %d, %Y"),
        "reviewer": reviewer,
        "heatmap": {
            "projects": heatmap_projects,
            "fields": [c[0] for c in _HEATMAP_COLUMNS],
            "z": heatmap_z,
        },
        # Rule-of-thumb constants shipped into the JS so the classification-
        # override recompute path reads the SAME calibration as Python.
        # Keeps the two sides in sync if we ever recalibrate.
        "constants": {
            "irrPctPerCent": IRR_PCT_PER_CENT,
            "calibrationSponsorFraction": CALIBRATION_SPONSOR_FRACTION,
            "haircutImpactPerPct": 0.014,  # JS-only today; see recomputeImpactFromClassify
            "opexNpvFactor": OPEX_NPV_FACTOR,
            "opexTermYears": OPEX_TERM_YEARS,
        },
    }
    return projects_list, portfolio


def render_html(
    m1_projects: dict,
    *,
    model_label: str = "Model",
    reviewer: str = "Caroline Z.",
    bible_label: str = "Q1 '26",
    walk_available: bool = False,
    walk_summary: dict | None = None,
) -> str:
    """Return the mockup HTML with real project data injected."""
    projects_list, portfolio = build_payload(
        m1_projects,
        model_label=model_label,
        reviewer=reviewer,
        bible_label=bible_label,
    )
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = (
        "/* __INJECT_DATA_START__ (runtime) */\n"
        f"let PORTFOLIO = {_safe_json(portfolio)};\n"
        f"let PROJECTS = {_safe_json(projects_list)};\n"
        f"let WALK_AVAILABLE = {'true' if walk_available else 'false'};\n"
        f"let WALK_SUMMARY = {_safe_json(walk_summary or {})};\n"
        "/* __INJECT_DATA_END__ */"
    )
    if not _INJECT_RE.search(template):
        # Marker missing — return template unchanged rather than silently failing
        return template
    return _INJECT_RE.sub(lambda _m: payload, template, count=1)


def render_empty_html(
    *,
    reviewer: str = "Caroline Z.",
    bible_label: str = "Q1 '26",
) -> str:
    """Render the mockup in the 'no projects loaded' empty state."""
    return render_html({}, model_label="No model loaded", reviewer=reviewer, bible_label=bible_label)
