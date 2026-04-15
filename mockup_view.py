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
ROW_NPP = 38
ROW_FMV_IRR = 33
ROW_ITC_PCT = 597


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


def _build_findings(audit: dict) -> list[dict]:
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
        findings.append({
            "field": str(field_label),
            "short": _short(str(field_label)),
            "bible": bible_str,
            "model": model_str,
            "delta": delta_n,
            "deltaUnit": unit,
            "impact": None,
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
    # Sort by severity: OFF first, then OUT, then others; limit to 6
    order = {"OFF": 0, "OUT": 1, "REVIEW": 2, "MISSING": 3}
    sliced = sorted(findings, key=lambda f: order.get(f["status"], 9))[:6]
    if not sliced:
        return {"labels": ["No findings"], "x": [0], "txt": ["—"], "colors": ["miss"]}
    # Bar size: placeholder severity weight (we don't have dollar impacts yet)
    labels, xs, txts, colors = [], [], [], []
    weight = {"OFF": -100, "OUT": -30, "REVIEW": 0, "MISSING": 0}
    color_map = {"OFF": "off", "OUT": "out", "REVIEW": "miss", "MISSING": "miss"}
    for f in sliced:
        labels.append(f.get("short") or f["field"][:20])
        xs.append(weight.get(f["status"], 0))
        txts.append(f["status"])
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
    findings = _build_findings(audit)
    summary = audit.get("summary", {}) or {}
    data = proj.get("data", {})
    dc_mw = _num(data.get(ROW_DC_MW)) or 0
    # Scale chart multipliers roughly by project size
    mul = max(0.5, min(3.5, dc_mw / 5.0)) if dc_mw else 1.0
    return {
        "name": proj.get("name") or "Unnamed",
        "sub": _derive_sub(proj, audit, label),
        "verdict": _verdict_from_summary(summary),
        "irrPct": 0,
        "nppPerW": 0,
        "equityK": 0,
        "kpis": _build_kpis(proj, findings),
        "findings": findings,
        "variance": _build_variance(findings),
        "stack": {
            "model": [0.50, 0.70, 1.15, 0.85],
            "bible": [0.50, 0.70, 1.15, 0.85],
        },
        "wrappedEpcComponents": _build_wrapped_epc(audit),
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
