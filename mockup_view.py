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
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from bible_audit import audit_project
from bible_reference import CS_AVERAGE, CS_STATE_OVERRIDES, lookup_market

_TEMPLATE_PATH = Path(__file__).parent / "VP_Review_Mockup.html"
_INJECT_RE = re.compile(
    r"/\* __INJECT_DATA_START__[\s\S]*?__INJECT_DATA_END__ \*/",
    re.MULTILINE,
)

# Key input rows in the pricing model — see data_loader.py
ROW_DC_MW = 11
ROW_AC_KW = 12
ROW_STATE = 18
ROW_UTILITY = 19
ROW_PROGRAM_A = 22
ROW_PROGRAM_B = 21
ROW_EPC_WRAPPED = 118
ROW_LNTP = 119
ROW_CLOSING = 123
ROW_NPP = 38
ROW_FMV_IRR = 33
ROW_UPFRONT = 216
ROW_INSURANCE = 296
ROW_ITC_PCT = 597
ROW_ELIG_COSTS = 602

# Rule-of-thumb: 1 cent/W swing in sponsor proceeds ≈ 0.18% FMV IRR.
IRR_PCT_PER_CENT = 0.18
# NPV dampener for multi-year OpEx deltas (rough 7% WACC, 25-yr).
OPEX_NPV_FACTOR = 0.55
OPEX_TERM_YEARS = 25


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("$", "").replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _pct(v: Any) -> str:
    n = _num(v)
    if n is None:
        return "—"
    # Model stores percentages as decimals (0.4) or whole numbers (40)
    display = n * 100 if abs(n) <= 1.5 else n
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
            display = v * 100 if abs(v) <= 1.5 else v
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
    """Treat 0.4 and 40 both as 40%."""
    n = _num(v)
    if n is None:
        return None
    return n if abs(n) <= 1.5 else n / 100.0


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
        epc = _num(data.get(ROW_EPC_WRAPPED)) or 1.65
        if "itc" in label or "tax credit" in label:
            elig = _as_fraction(data.get(ROW_ELIG_COSTS)) or 0.97
            exp_f = _as_fraction(exp)
            act_f = _as_fraction(act)
            if exp_f is None or act_f is None:
                return None
            return (act_f - exp_f) * elig * epc * dc_w
        if "eligible" in label:
            itc = _as_fraction(data.get(ROW_ITC_PCT)) or 0.40
            exp_f = _as_fraction(exp)
            act_f = _as_fraction(act)
            if exp_f is None or act_f is None:
                return None
            return (act_f - exp_f) * itc * epc * dc_w
        return None

    if unit in ("$/MW/yr", "$/MW-dc/yr"):
        # OpEx: higher actual = downside → flip sign, amortize over term with NPV dampener
        return -delta * dc_mw * OPEX_TERM_YEARS * OPEX_NPV_FACTOR

    if unit == "$/kWh":
        # Rate-level OpEx (cust mgmt). Approximate annual MWh at 1,550 kWh/Wp × DC_MW.
        annual_mwh = dc_mw * 1_550
        return -delta * annual_mwh * OPEX_TERM_YEARS * OPEX_NPV_FACTOR

    return None


def _roll_up(findings: list[dict], dc_mw: float) -> dict:
    total = 0.0
    for f in findings:
        v = f.get("impact")
        if isinstance(v, (int, float)):
            total += v
    if dc_mw > 0:
        npp_per_w = total / (dc_mw * 1_000_000)
    else:
        npp_per_w = 0.0
    irr_pct = (npp_per_w / 0.01) * IRR_PCT_PER_CENT
    return {
        "nppPerW": round(npp_per_w, 3),
        "irrPct": round(irr_pct, 2),
        "equityK": int(round(total / 1000)),
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

    # Bible (cross-market + IL insurance override if applicable)
    cs = dict(CS_AVERAGE)
    overrides = CS_STATE_OVERRIDES.get(state) or (CS_STATE_OVERRIDES.get("MD") if state in ("MD", "DE") else {})
    if overrides:
        cs = {**cs, **overrides}

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
            rec_s = f"{rec_term}-yr" if isinstance(rec_term, (int, float)) else (str(rec_term) if rec_term else "")
            market_items.append({"k": "REC Rate", "v": rec_v, "s": rec_s})
        if market.get("post_rec_rate") not in (None, 0):
            prr = market.get("post_rec_rate"); prt = market.get("post_rec_term")
            market_items.append({
                "k": "Post-REC Rate",
                "v": f"${prr:,.2f}/MWh" if isinstance(prr, (int, float)) else str(prr),
                "s": f"{prt}-yr" if prt else "",
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
    itc = _num(data.get(ROW_ITC_PCT))
    irr = _num(data.get(ROW_FMV_IRR))
    epc_off = any(f["status"] == "OFF" and "EPC" in f["field"].upper() for f in findings)
    itc_off = any(f["status"] == "OFF" and "ITC" in f["field"].upper() for f in findings)

    irr_display = None
    if irr is not None:
        val = irr * 100 if abs(irr) <= 1.5 else irr
        irr_display = f"{val:.1f}%"

    itc_display = None
    if itc is not None:
        val = itc * 100 if abs(itc) <= 1.5 else itc
        itc_display = f"{val:.0f}%"

    return {
        "dc": f"{dc_mw:.2f}" if dc_mw else "—",
        "dcSub": f"{ac_mw:.2f} MW AC" if ac_mw else "",
        "epc": _money_per_w(epc),
        "epcSub": "",
        "epcOff": bool(epc_off),
        "npp": _money_per_w(npp),
        "nppSub": "",
        "itc": itc_display or "—",
        "itcSub": "",
        "itcOff": bool(itc_off),
        "irr": irr_display or "—",
        "irrSub": "",
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


def _build_mockup_project(proj: dict, audit: dict, label: str) -> dict:
    data = proj.get("data", {})
    findings = _build_findings(audit, data)
    summary = audit.get("summary", {}) or {}
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    rolled = _roll_up(findings, dc_mw)
    # Scale chart multipliers roughly by project size
    mul = max(0.5, min(3.5, dc_mw / 5.0)) if dc_mw else 1.0
    return {
        "name": proj.get("name") or "Unnamed",
        "sub": _derive_sub(proj, audit, label),
        "verdict": _verdict_from_summary(summary),
        "irrPct": rolled["irrPct"],
        "nppPerW": rolled["nppPerW"],
        "equityK": rolled["equityK"],
        "kpis": _build_kpis(proj, findings),
        "findings": findings,
        "variance": _build_variance(findings),
        "stack": {
            "model": [0.50, 0.70, 1.15, 0.85],
            "bible": [0.50, 0.70, 1.15, 0.85],
        },
        "wrappedEpcComponents": _build_wrapped_epc(audit),
        "references": _build_references(proj, audit),
        "cashflowMul": round(mul, 2),
        "tornadoMul": round(mul, 2),
    }


def _safe_audit(proj_data: dict) -> dict:
    try:
        return audit_project(proj_data)
    except Exception:
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


def _default_json(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)


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

    for _, proj in _iter_projects(m1_projects):
        if not proj.get("toggle", True):
            continue
        audit = _safe_audit(proj.get("data", {}))
        projects_list.append(_build_mockup_project(proj, audit, model_label))
        summary = audit.get("summary", {}) or {}
        for k in totals:
            totals[k] += summary.get(k, 0) or 0
        mw = _num(proj.get("data", {}).get(ROW_DC_MW)) or 0
        total_mw += mw

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
    }
    return projects_list, portfolio


def render_html(
    m1_projects: dict,
    *,
    model_label: str = "Model",
    reviewer: str = "Caroline Z.",
    bible_label: str = "Q1 '26",
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
        f"let PORTFOLIO = {json.dumps(portfolio, default=_default_json)};\n"
        f"let PROJECTS = {json.dumps(projects_list, default=_default_json)};\n"
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
