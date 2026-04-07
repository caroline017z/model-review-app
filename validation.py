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
