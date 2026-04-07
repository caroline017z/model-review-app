"""
38DN Pricing Model Review — Validation Engine
Validates project inputs against Pricing Bible benchmarks.
"""
from utils import safe_float


def validate_project(proj_data, benchmarks):
    """Validate a project's data against benchmark ranges. Returns (findings, state)."""
    findings = []
    state = str(proj_data.get(18, "")).strip().upper()

    for category, checks in benchmarks.items():
        for label, spec in checks.items():
            if spec.get("derived"):
                num = safe_float(proj_data.get(spec["num_row"]))
                den = safe_float(proj_data.get(spec["den_row"]))
                val = num / den if num and den and den > 0 else None
                row_ref = f"{spec['num_row']}/{spec['den_row']}"
            else:
                val = safe_float(proj_data.get(spec["row"]))
                row_ref = str(spec["row"])

            if val is None:
                findings.append({
                    "Category": category, "Check": label, "Row": row_ref,
                    "Value": None, "Min": spec["min"], "Max": spec["max"],
                    "Unit": spec["unit"], "Status": "WARNING",
                    "Note": "Blank / non-numeric",
                })
                continue

            if val < spec["min"]:
                status, note = "LOW", f"Below min ({spec['min']})"
            elif val > spec["max"]:
                status, note = "HIGH", f"Above max ({spec['max']})"
            else:
                status, note = "OK", ""

            findings.append({
                "Category": category, "Check": label, "Row": row_ref,
                "Value": val, "Min": spec["min"], "Max": spec["max"],
                "Unit": spec["unit"], "Status": status, "Note": note,
            })

    return findings, state


def summarize_findings(findings):
    """Build a compact status summary from row-level findings."""
    summary = {"total": 0, "ok": 0, "warning": 0, "low": 0, "high": 0}
    for item in findings or []:
        summary["total"] += 1
        status = str(item.get("Status", "")).upper()
        if status == "OK":
            summary["ok"] += 1
        elif status == "WARNING":
            summary["warning"] += 1
        elif status == "LOW":
            summary["low"] += 1
        elif status == "HIGH":
            summary["high"] += 1
    return summary


def build_assumption_alignment(proj_data, benchmarks):
    """
    Create structured output that highlights where inputs diverge from base assumptions.
    Returns a dict with summary totals and sorted exceptions for quick M&A bid triage.
    """
    findings, _ = validate_project(proj_data, benchmarks)
    summary = summarize_findings(findings)

    exceptions = []
    for item in findings:
        status = item.get("Status")
        if status not in {"LOW", "HIGH", "WARNING"}:
            continue
        min_val = item.get("Min")
        max_val = item.get("Max")
        value = item.get("Value")
        if value is None:
            variance = None
        elif status == "LOW":
            variance = value - min_val
        elif status == "HIGH":
            variance = value - max_val
        else:
            variance = None

        exceptions.append({
            "Category": item.get("Category"),
            "Check": item.get("Check"),
            "Status": status,
            "Value": value,
            "Expected Min": min_val,
            "Expected Max": max_val,
            "Variance": variance,
            "Row": item.get("Row"),
            "Note": item.get("Note"),
        })

    exceptions.sort(key=lambda x: (x["Category"] or "", x["Check"] or ""))
    return {
        "summary": summary,
        "exceptions": exceptions,
        "findings": findings,
    }
