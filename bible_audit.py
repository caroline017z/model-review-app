"""
38DN Pricing Model Review — Bible Audit Engine

Cross-references project inputs against canonical Q1 '26 bible values.
Combines two check styles:
  - RANGE  : value must fall within [min, max] (existing BIBLE_BENCHMARKS)
  - EXACT  : value must equal bible value within tolerance (CS_AVERAGE +
             per-market MARKET_BIBLE entries)

Returns per-row dicts that the UI can use for inline highlighting:

    {row: {"status": "OK" | "OFF" | "OUT" | "MISSING" | "REVIEW",
           "expected": <bible value or "S-SFA"/"TBD">,
           "actual":   <model value>,
           "tol":      <tolerance>,
           "note":     "<short reason>"} }

Status legend:
    OK       — within tolerance / inside range
    OFF      — exact-match failed (red)
    OUT      — outside range (yellow)
    MISSING  — model cell blank where bible expects a value
    REVIEW   — bible references an external lookup (S-SFA, TBD); manual review
"""
from utils import safe_float
from bible_reference import (
    CS_AVERAGE, CS_STATE_OVERRIDES, MARKET_BIBLE, lookup_market, SSFA, TBD,
)
from config import BIBLE_BENCHMARKS


# Tolerance defaults when CS_AVERAGE entry omits "tol"
_DEFAULT_PCT_TOL    = 0.0      # exact match for percentages
_DEFAULT_MONEY_TOL  = 0.0      # exact match for $ values
_NUMERIC_EPSILON    = 1e-9


def _normalize_state(state):
    if not state:
        return ""
    s = str(state).strip().upper()
    if s in ("MD", "DE"):
        return "MD/DE"
    return s


def _exact_check(actual, expected, tol, unit=""):
    """Return (status, note) for a single exact-match comparison.

    When the field is a percentage (unit='%') or when the two sides disagree
    by >100x in magnitude, normalize both to fractions (0.40) before diffing.
    This prevents false OFFs when a model stores ITC as 40 and the bible
    stores 0.40 — same economic value, different unit convention.
    """
    a = safe_float(actual)
    e = safe_float(expected)
    if a is None:
        return "MISSING", "Model cell blank"
    if e is None:
        # Expected is a string sentinel/lookup
        if expected in (SSFA, TBD) or isinstance(expected, str):
            return "REVIEW", f"Bible: {expected}"
        return "REVIEW", "Bible non-numeric"

    # Pct/fraction normalization: if either unit is "%" or the magnitudes
    # disagree by enough to suggest one side is whole-percent and the other
    # fractional, scale both to fractions before comparing.
    needs_norm = (str(unit or "").strip() == "%") or (
        (abs(a) > 1.5 and abs(e) <= 1.5) or (abs(e) > 1.5 and abs(a) <= 1.5)
    )
    if needs_norm:
        if abs(a) > 1.5:
            a = a / 100.0
        if abs(e) > 1.5:
            e = e / 100.0

    diff = abs(a - e)
    if diff <= (tol or 0) + _NUMERIC_EPSILON:
        return "OK", ""
    sign = "+" if a > e else "−"
    return "OFF", f"{sign}{diff:.4g} vs bible {e:.4g}"


def _range_check(actual, spec):
    """Return (status, note) for a range check from BIBLE_BENCHMARKS."""
    val = safe_float(actual)
    if val is None:
        return "MISSING", "Model cell blank"
    lo, hi = spec["min"], spec["max"]
    if val < lo:
        return "OUT", f"Below min ({lo})"
    if val > hi:
        return "OUT", f"Above max ({hi})"
    return "OK", ""


# ---------------------------------------------------------------------------
# Per-project audit
# ---------------------------------------------------------------------------

def audit_project(proj_data):
    """Audit one project. Returns {row: result_dict} keyed by model row.

    proj_data: dict {row_number: cell_value} — typically projects[col]["data"].
    """
    state = _normalize_state(proj_data.get(18))
    utility = proj_data.get(19)
    # Program lives in different rows depending on model — try a couple
    program = proj_data.get(22) or proj_data.get(21)

    # ABP REC LIVE OVERRIDE -------------------------------------------------
    # If an "ABP REC" rate component is toggled on for the equity model,
    # treat the project as ABP regardless of how the program field is labeled.
    # Many models label the program "Community" or leave it blank when ABP
    # REC revenue is the live rate path — that mismatch breaks lookup_market
    # for IL Ameren / IL ComEd. Forcing program="ABP" recovers the correct
    # market entry. data_loader sets _abp_rec_live by scanning rate-component
    # names for "ABP REC" and checking the equity toggle.
    abp_rec_live = bool(proj_data.get("_abp_rec_live"))
    program_used = program
    market_source_note = ""
    if abp_rec_live and state == "IL":
        program_used = "ABP"
        market_source_note = " [ABP REC live → forced ABP lookup]"

    market = lookup_market(state, utility, program_used)
    if market is None and abp_rec_live:
        # Final fallback: try plain "ABP" string
        market = lookup_market(state, utility, "ABP")
        if market is not None and not market_source_note:
            market_source_note = " [ABP REC live → forced ABP lookup]"

    findings = {}

    # ---- 1. CS_AVERAGE: cross-market exact-match ----
    for row, spec in CS_AVERAGE.items():
        expected = spec["value"]
        tol = spec.get("tol", _DEFAULT_MONEY_TOL)
        # State override?
        override = CS_STATE_OVERRIDES.get(state, {}).get(row)
        if override:
            expected = override["value"]
            tol = override.get("tol", tol)

        unit = spec.get("unit", "")
        status, note = _exact_check(proj_data.get(row), expected, tol, unit)
        findings[row] = {
            "status": status, "expected": expected, "actual": proj_data.get(row),
            "tol": tol, "note": note, "source": "CS Average" + (f" [{state} override]" if override else ""),
            "label": spec.get("label", ""), "unit": unit,
        }

    # ---- 2. MARKET_BIBLE: per (state,utility,program) exact-match ----
    if market:
        # Iterate only numeric/sentinel row keys (skip metadata strings like
        # "rec_rate", "incentive_detail" which aren't model rows)
        for k, expected in market.items():
            if not isinstance(k, int):
                continue
            tol = 0.0  # tight match for market values
            # Market values for pct rows (161, 162, 240) are stored as fractions;
            # the _exact_check magnitude guard handles unit drift either way.
            status, note = _exact_check(proj_data.get(k), expected, tol)
            findings[k] = {
                "status": status, "expected": expected, "actual": proj_data.get(k),
                "tol": tol, "note": note,
                "source": f"Market: {state}/{utility}/{program_used}{market_source_note}",
                "label": "", "unit": "",
            }

    # ---- 3. BIBLE_BENCHMARKS: range checks (CapEx, sizing, etc.) ----
    # Range checks AUGMENT exact-match: if a row already has an exact-match
    # OFF, range still adds context. We store under a sub-key to avoid clobber.
    for category, checks in BIBLE_BENCHMARKS.items():
        for label, spec in checks.items():
            if spec.get("derived"):
                continue  # derived checks handled separately if needed
            row = spec["row"]
            status, note = _range_check(proj_data.get(row), spec)
            existing = findings.get(row)
            if existing:
                # Merge: prefer OFF over OUT; promote MISSING to OUT if range fails
                if existing["status"] == "OK" and status == "OUT":
                    existing["status"] = "OUT"
                    existing["note"] = (existing.get("note") + "; " if existing.get("note") else "") + note
                    existing["range"] = (spec["min"], spec["max"])
                elif existing["status"] in ("MISSING", "REVIEW") and status != "OK":
                    existing["status"] = status
                    existing["note"] = note
                    existing["range"] = (spec["min"], spec["max"])
                else:
                    existing["range"] = (spec["min"], spec["max"])
            else:
                findings[row] = {
                    "status": status, "expected": None, "actual": proj_data.get(row),
                    "tol": None, "note": note,
                    "source": f"Range: {category}", "label": label,
                    "unit": spec.get("unit", ""), "range": (spec["min"], spec["max"]),
                }

    # ---- 4. GUIDEHOUSE DISCOUNT: rate-component-level audit ----
    # data_loader scans rate-component names for "Guidehouse" / "GH" and
    # returns each match with its applied discount %. The bible expects a
    # specific Guidehouse-derived discount per market; we surface the actual
    # values for the UI to highlight without forcing an exact-match (the
    # expected % is market- and tier-specific and lives in MARKET_BIBLE).
    guidehouse = proj_data.get("_guidehouse_components") or []
    guidehouse_audit = []
    expected_disc = (market or {}).get("rate_discount") if market else None
    for comp in guidehouse:
        actual = comp.get("discount")
        if actual is None:
            status, note = "MISSING", "Guidehouse discount not entered"
        elif expected_disc is None:
            status, note = "REVIEW", "No bible Guidehouse discount for this market"
        else:
            diff = abs(actual - expected_disc)
            if diff <= 0.005:   # 0.5% tolerance
                status, note = "OK", ""
            else:
                sign = "+" if actual > expected_disc else "−"
                status = "OFF"
                note = f"{sign}{diff*100:.2f} pp vs bible {expected_disc*100:.2f}%"
        guidehouse_audit.append({
            "rate_idx": comp["idx"], "name": comp["name"],
            "actual": actual, "expected": expected_disc,
            "equity_on": comp["equity_on"], "status": status, "note": note,
        })

    # ---- 5. WRAPPED EPC: surface the build for transparency ----
    wrapped_components = proj_data.get("_wrapped_epc_components") or []
    wrapped_total = proj_data.get("_wrapped_epc_total")

    return {
        "rows": findings,
        "state": state, "utility": utility, "program": program,
        "program_used": program_used,
        "abp_rec_live": abp_rec_live,
        "market_matched": market is not None,
        "guidehouse": guidehouse_audit,
        "wrapped_epc": {
            "components": wrapped_components,
            "total": wrapped_total,
            "raw_epc": proj_data.get("_raw_epc_118"),
        },
        "summary": _summarize(findings),
    }


def _summarize(findings):
    counts = {"OK": 0, "OFF": 0, "OUT": 0, "MISSING": 0, "REVIEW": 0}
    for f in findings.values():
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    return counts


def audit_projects(projects):
    """Audit a dict of projects. Returns {col: audit_result}."""
    results = {}
    for col, proj in projects.items():
        data = proj["data"] if isinstance(proj, dict) and "data" in proj else proj
        results[col] = audit_project(data)
    return results


# ---------------------------------------------------------------------------
# Inline-highlight helpers (consumed by app.py / comparison rendering)
# ---------------------------------------------------------------------------

# CSS class per status — applied to comparison-table <td>
STATUS_CSS = {
    "OK":      "",
    "OFF":     "audit-off",       # red — exact mismatch
    "OUT":     "audit-out",       # yellow — out of range
    "MISSING": "audit-missing",   # grey — blank
    "REVIEW":  "audit-review",    # blue — manual review (S-SFA / TBD)
}


def status_class(audit_result, row):
    """Return the CSS class for a model row's audit status, or '' if no finding."""
    if not audit_result:
        return ""
    f = audit_result.get("rows", {}).get(row)
    if not f:
        return ""
    return STATUS_CSS.get(f["status"], "")


def status_tooltip(audit_result, row):
    """Build a hover-tooltip string for a row's audit finding."""
    if not audit_result:
        return ""
    f = audit_result.get("rows", {}).get(row)
    if not f:
        return ""
    parts = [f"Status: {f['status']}"]
    if f.get("expected") is not None:
        parts.append(f"Bible: {f['expected']} {f.get('unit','')}".strip())
    if f.get("range"):
        lo, hi = f["range"]
        parts.append(f"Range: {lo}–{hi}")
    if f.get("note"):
        parts.append(f["note"])
    if f.get("source"):
        parts.append(f"({f['source']})")
    return " | ".join(parts)
