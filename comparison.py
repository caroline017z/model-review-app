"""
38DN Pricing Model Review — Comparison & Portfolio Logic
Model comparison tables and MWdc-weighted portfolio averages.
"""
import pandas as pd

from config import INPUT_ROW_LABELS, OUTPUT_ROWS, TEXT_ROWS, DATE_ROWS, PCT_ROWS, DISPLAY_ORDER
from utils import safe_float, fmt_val, fmt_delta, fmt_row_val


def build_comparison_table(proj1_data, proj2_data, proj_name, m1_label, m2_label):
    """Build a comparison dataframe for a single project across two models."""
    all_rows = [r for r in DISPLAY_ORDER if r in INPUT_ROW_LABELS or r in OUTPUT_ROWS]
    comp_rows = []

    for r in all_rows:
        label = INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}"))
        v1_raw = proj1_data.get(r)
        v2_raw = proj2_data.get(r) if proj2_data else None

        if r in TEXT_ROWS or r in DATE_ROWS:
            comp_rows.append({
                "Row": r, "Field": label,
                m1_label: fmt_row_val(v1_raw, r),
                m2_label: fmt_row_val(v2_raw, r),
                "Delta": "", "\u0394 %": "",
                "_delta_raw": None, "_pct_raw": None,
            })
            continue

        v1 = safe_float(v1_raw)
        v2 = safe_float(v2_raw)
        is_pct = r in PCT_ROWS

        if v1 is not None and v2 is not None:
            delta = v2 - v1
            pct_diff = delta / abs(v1) if v1 != 0 else None
        else:
            delta = None
            pct_diff = None

        comp_rows.append({
            "Row": r, "Field": label,
            m1_label: fmt_row_val(v1, r),
            m2_label: fmt_row_val(v2, r),
            "Delta": fmt_delta(delta, is_pct),
            "\u0394 %": fmt_delta(pct_diff, pct_fmt=True),
            "_delta_raw": delta, "_pct_raw": pct_diff,
        })

    return pd.DataFrame(comp_rows)


def compute_portfolio_wtd_avg(active_projects):
    """Compute MWdc-weighted average for all numeric rows across active projects."""
    if not active_projects:
        return {"_total_mw": 0, "_proj_count": 0}

    total_mw = 0
    wtd_sums = {}
    proj_count = len(active_projects)
    text_vals = {}

    for proj in (active_projects.values() if isinstance(active_projects, dict) else active_projects):
        d = proj["data"] if isinstance(proj, dict) and "data" in proj else proj
        mw = safe_float(d.get(11)) or 0
        total_mw += mw
        for r in sorted(set(INPUT_ROW_LABELS.keys()) | set(OUTPUT_ROWS.keys())):
            if r in TEXT_ROWS or r in DATE_ROWS:
                val = d.get(r)
                text_vals.setdefault(r, []).append(fmt_row_val(val, r) if val else "")
                continue
            v = safe_float(d.get(r))
            if v is not None and mw > 0:
                wtd_sums.setdefault(r, 0)
                wtd_sums[r] += v * mw

    result = {"_total_mw": total_mw, "_proj_count": proj_count}
    for r, ws in wtd_sums.items():
        result[r] = ws / total_mw if total_mw > 0 else None
    for r, vals in text_vals.items():
        unique = list(set(v for v in vals if v and v != "\u2014"))
        result[r] = unique[0] if len(unique) == 1 else " / ".join(unique[:3])
    result[11] = total_mw  # Size = total, not avg

    npps = [safe_float((p["data"] if isinstance(p, dict) and "data" in p else p).get(39))
            for p in (active_projects.values() if isinstance(active_projects, dict) else active_projects)]
    result[39] = sum(v for v in npps if v is not None) or None

    return result


def render_bible_section(title, data_dict, value_key="value", show_notes=True):
    rows = []
    for name, info in data_dict.items():
        row = {"Assumption": name, "Q1 '26 Avg": info.get(value_key, ""), "Unit": info.get("unit", "")}
        if "esc" in info and info["esc"] is not None:
            row["Escalator"] = f"{info['esc']:.1%}"
        if show_notes:
            row["Note"] = info.get("note", "")
        rows.append(row)
    return pd.DataFrame(rows)


def render_market_card(cfg):
    lines = []
    inc = cfg.get("upfront_incentive", 0)
    if inc:
        detail = cfg.get("incentive_detail", "")
        lines.append(f"**Upfront Incentive:** ${inc:.3f}/W ({detail})" if detail else f"**Upfront Incentive:** ${inc:.3f}/W")
        lines.append(f"**Incentive Lag:** {cfg.get('incentive_lag', 0)} months")
    resi = cfg.get("cust_resi", 0)
    if isinstance(resi, str):
        lines.append(f"**Customer Mix:** {resi}")
    else:
        mix = []
        for seg, k in [("Resi", "cust_resi"), ("Comm", "cust_comm"), ("Anchor", "cust_anchor"), ("LMI", "cust_lmi")]:
            v = cfg.get(k, 0)
            if isinstance(v, (int, float)) and v > 0:
                mix.append(f"{seg} {v:.0%}")
        if mix:
            lines.append(f"**Customer Mix:** {' / '.join(mix)}")
    db = cfg.get("disc_blend")
    if isinstance(db, (int, float)):
        lines.append(f"**Blended Discount:** {db:.0%}")
    elif isinstance(db, str):
        lines.append(f"**Blended Discount:** {db}")
    acq = cfg.get("acq_blend")
    if acq:
        lines.append(f"**Blended Cust Acq:** ${acq:.4f}/kWh")
    ucb = cfg.get("ucb", 0)
    if ucb:
        lines.append(f"**UCB Fee:** {ucb:.1%}")
    lines.append(f"**Rate Curve:** {cfg.get('rate_curve', '')}")
    lines.append(f"**Rate Source:** {cfg.get('rate_source', '')}")
    rec = cfg.get("rec_rate", 0)
    lines.append(f"**REC Rate:** {'$' + str(rec) + '/MWh' if isinstance(rec, (int, float)) else str(rec)}")
    lines.append(f"**REC Term:** {cfg.get('rec_term', '')} yrs | **Post-REC:** ${cfg.get('post_rec', 0)}/MWh for {cfg.get('post_rec_term', '')} yrs")
    return "\n\n".join(lines)
