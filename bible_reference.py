"""
38DN Pricing Model Review — Pricing Bible Reference (Q1 2026)
Canonical truth for audit cross-reference. Values extracted from:
  - Internal Pricing Bible Q1 2026, "CS" tab, Average column (col H)
  - Internal Pricing Bible Q1 2026, "Market Specifc Assumptions" tab

Each entry below maps a model row number (matching config.INPUT_ROW_LABELS)
to the bible-canonical value or per-market lookup. The audit engine consumes
these dicts in bible_audit.py.

When the bible is updated, edit these literals only — no parser at runtime.
"""

# =====================================================================
# CS TAB — Q1 '26 Average (cross-market constants)
# Row keys are model row numbers from config.INPUT_ROW_LABELS
# =====================================================================

CS_AVERAGE = {
    # CapEx ($/W)
    118: {"value": 1.65,   "unit": "$/W",       "tol": 0.10,   "label": "PV EPC Cost",
          "note": ">5 MWdc avg; <5 MWdc=$1.75; PA ~10c cheaper"},
    119: {"value": 0.10,   "unit": "$/W",       "tol": 0.02,   "label": "PV LNTP Cost",
          "note": "4-6 MW standard"},
    123: {"value": 0.06,   "unit": "$/W",       "tol": 0.015,  "label": "Closing and Legal"},

    # OpEx
    225: {"value": 4750,   "unit": "$/MW/yr",   "tol": 250,    "label": "PV O&M Preventative",
          "note": "Up from $4,500 in Q2"},
    226: {"value": 2000,   "unit": "$/MW/yr",   "tol": 100,    "label": "PV O&M Corrective"},
    227: {"value": 0.02,   "unit": "%",         "tol": 0.0,    "label": "PV O&M Esc"},
    230: {"value": 3000,   "unit": "$/MW/yr",   "tol": 0,      "label": "AM Fee (financing)"},
    231: {"value": 0.02,   "unit": "%",         "tol": 0.0,    "label": "AM Esc"},
    302: {"value": 2500,   "unit": "$/MW/yr",   "tol": 0,      "label": "Internal AM Costs"},
    241: {"value": 0.02,   "unit": "%",         "tol": 0.0,    "label": "Customer Mgmt Esc"},

    # Decom & insurance
    286: {"value": 0.025,  "unit": "% of bond", "tol": 0.0,    "label": "Decom Annual Premium"},
    296: {"value": 3500,   "unit": "$/MW-dc/yr", "tol": 0,     "label": "P&C Insurance",
          "note": "IL = $4,185/MW-dc/yr (separate market assumption); see state override"},
    297: {"value": 0.02,   "unit": "%",         "tol": 0.0,    "label": "P&C Insurance Esc"},

    # Financing — Tax Equity (cross-market)
    # Row mappings approximate; FMV WACC and TE pref aren't all on Project Inputs
    # but are useful for IC narrative checks.

    # Tax & ITC
    597: {"value": 0.40,   "unit": "%",         "tol": 0.0,    "label": "ITC Rate"},
    602: {"value": 0.97,   "unit": "%",         "tol": 0.03,   "label": "Eligible Costs %"},
}

# State-specific overrides applied on top of CS_AVERAGE (matched on row 18)
CS_STATE_OVERRIDES = {
    "IL": {
        # Separate market assumption noted on the side of the bible CS column —
        # IL hail risk premium. Unit basis is $/MW-dc/yr (not kW-yr).
        296: {"value": 4815, "unit": "$/MW-dc/yr", "tol": 0,
              "label": "P&C Insurance (IL hail premium)"},
    },
}

# EPC Spend Curve (rows 117 child curves — informational)
CS_EPC_SPEND_CURVE = {
    "Month 0": 0.00, "Month 1 (NTP+)": 0.15, "Month 2": 0.05, "Month 3": 0.00,
    "Month 4": 0.20, "Month 5": 0.10, "Month 6": 0.10, "Month 7": 0.15,
    "Month 8": 0.05, "Month 9": 0.00, "Month 10": 0.05, "Month 11": 0.10,
    "Month 12": 0.00, "Month 13": 0.00, "Month 14": 0.05,
}

# Tax-equity flip assumptions (CS tab — Q1 '26 Average)
CS_TAX_EQUITY = {
    "fmv_step_up_cap":   0.30,
    "fmv_wacc":          0.0725,   # NY=0.07 (BDO), IL=0.08
    "ppc":               1.06,
    "te_buyout":         0.07,
    "te_pref":           0.025,
    "im_te_variable":    0.01,
    "te_insurance":      0.035,    # full ITC basis
    "te_insurance_basis":"Full ITC",
}

# Permanent debt — front leverage (Q1 '26 Average)
CS_PERM_DEBT_FRONT = {
    "tenor_yrs":          25,
    "base_rate_25yr":     0.04995,
    "base_rate_7yr":      0.04408,
    "rate_step_up_7yr":   0.004,
    "margin":             0.022,
    "usda_fee":           14500,
    "structuring_usda":   0.0105,
    "structuring_non":    0.015,
    "dscr_yr1":           2.00, "dscr_yr2": 1.75, "dscr_yr3": 1.60,
    "dscr_yr4":           1.60, "dscr_yr5": 1.60, "dscr_yr6_plus": 1.35,
}

# Permanent debt — back leverage (Q1 '26 Average)
CS_PERM_DEBT_BACK = {
    "tenor_yrs":          7,
    "base_rate":          0.0404,
    "margin":             0.025,    # IL=0.0275
    "closing_fee":        0.015,    # IL=0.015, others 0.01-0.0125
    "dscr_yr1":           2.00, "dscr_yr2": 1.75, "dscr_yr3": 1.60,
    "dscr_yr4":           1.60, "dscr_yr5": 1.60,
    "dscr_yr6_fixed":     1.30, "dscr_yr6_ptc": 1.40, "dscr_yr6_wholesale": 1.75,
}

# Construction loan (Q1 '26 Average)
CS_CONSTRUCTION_LOAN = {
    "base_rate":          0.0365,    # T6M SOFR
    "margin":             0.0265,
    "origination_fee":    0.01,
    "max_advance_rate":   0.90,
}


# =====================================================================
# MARKET SPECIFIC ASSUMPTIONS — keyed on (state, utility, program)
# Maps to row-level bible values for per-project audit
# =====================================================================

# Helper sentinel for non-numeric / lookup-driven cells (e.g. NY S-SFA pricing).
# When the bible value is one of these, the audit skips exact-match comparison
# but flags missing values in the model with a "review" note.
SSFA = "S-SFA"
TBD  = "TBD"

# Each entry: model_row -> bible value (numeric or sentinel)
# Row mapping reference:
#   216 Upfront Incentive ($/W)
#   217 Upfront Incentive Lag (months)
#   161 Rate Discount (blended customer discount, %)
#   162 Rate UCB Fee (%)
#   240 Customer Mgmt Cost ($/kWh)
#   "rec_rate" / "rec_term" / "post_rec_rate" / "post_rec_term" — informational
#       (REC values often live in rate components, not a fixed row)

MARKET_BIBLE = {
    # ---------------- NY ----------------
    ("NY", "National Grid", "VDER (CS)"): {
        216: 0.175, 217: 3, 161: 0.0, 162: 0.015, 240: 0.0,
        "rec_rate": 31.03, "rec_term": 25, "post_rec_rate": 0, "post_rec_term": 10,
        "incentive_detail": "MW Block ($0.05) + Prevailing Wage ($0.125)",
        "rate_curve": "3Q25 TTM", "rate_source": "NYGB",
        "cust_mix": SSFA, "cust_discount": SSFA, "cust_acq": SSFA,
    },
    ("NY", "NYSEG", "VDER (CS)"): {
        216: 0.175, 217: 3, 161: 0.0, 162: 0.015, 240: 0.0,
        "rec_rate": 31.03, "rec_term": 25, "post_rec_rate": 0, "post_rec_term": 10,
        "rate_curve": "3Q25 TTM", "rate_source": "NYGB",
        "cust_mix": SSFA, "cust_discount": SSFA, "cust_acq": SSFA,
    },
    ("NY", "Other (Non-NG/NYSEG)", "VDER (CS)"): {
        216: 0.175, 217: 3, 161: 0.0, 162: 0.015, 240: 0.0,
        "rec_rate": 31.03, "rec_term": 25, "post_rec_rate": 0, "post_rec_term": 10,
        "rate_curve": "3Q25 TTM", "rate_source": "NYGB",
        "cust_mix": SSFA, "cust_discount": SSFA, "cust_acq": SSFA,
    },

    # ---------------- MD / DE — Delmarva ----------------
    ("MD/DE", "Delmarva", "MD PILOT"): {
        216: 0.0, 217: 0, 161: 0.10, 162: 0.01, 240: 0.0069,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 10,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_mix": "50% Resi / 50% Comm",
        "cust_acq_blend": 0.092,
    },
    ("MD/DE", "Delmarva", "MD Permanent"): {
        216: 0.0, 217: 0, 161: 0.20, 162: 0.01, 240: 0.0083,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 5,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_mix": "30% Resi / 20% Comm / 50% LMI",
        "cust_acq_blend": 0.0739,
    },
    ("MD/DE", "Potomac Edison", "MD PILOT"): {
        216: 0.0, 217: 0, 161: 0.10, 162: 0.01, 240: 0.00655,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 10,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0655,
    },
    ("MD/DE", "Potomac Edison", "MD Permanent"): {
        216: 0.0, 217: 0, 161: 0.15, 162: 0.01, 240: 0.0072,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 5,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0735,
    },
    ("MD/DE", "BGE", "MD PILOT"): {
        216: 0.0, 217: 0, 161: 0.08, 162: 0.01, 240: 0.00672,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 10,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0666,
    },
    ("MD/DE", "BGE", "MD Permanent"): {
        216: 0.0, 217: 0, 161: 0.13, 162: 0.01, 240: 0.00717,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 5,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0701,
    },
    ("MD/DE", "PEPCO", "MD PILOT"): {
        216: 0.0, 217: 0, 161: 0.08, 162: 0.01, 240: 0.00682,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 10,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0666,
    },
    ("MD/DE", "PEPCO", "MD Permanent"): {
        216: 0.0, 217: 0, 161: 0.19, 162: 0.01, 240: 0.00741,
        "rec_rate": "Y1-5: 43/33/31/26/21; Y6-10: 18", "rec_term": 5,
        "post_rec_rate": 3, "post_rec_term": 30,
        "cust_acq_blend": 0.0713,
    },

    # ---------------- IL ----------------
    ("IL", "Ameren", "ABP"): {
        216: 0.25, 217: 3, 161: 0.10, 162: 0.01, 240: 0.0049,
        "rec_rate": "Project Dependent", "rec_term": 20,
        "post_rec_rate": 3, "post_rec_term": 20,
        "incentive_detail": "Smart Inverter Rebate",
        "cust_acq_blend": 0.0366,
    },
    ("IL", "Ameren", "Non-ABP / PTC"): {
        216: 0.25, 217: 3, 161: 0.10, 162: 0.01, 240: 0.0049,
        "rec_rate": 3, "rec_term": "Full project life",
        "post_rec_rate": 3, "post_rec_term": "Remaining life",
        "incentive_detail": "Smart Inverter Rebate",
        "cust_acq_blend": 0.0366,
    },
    ("IL", "ComEd", "ABP"): {
        216: 0.25, 217: 3, 161: 0.10, 162: 0.01, 240: 0.00478,
        "rec_rate": "Project Dependent", "rec_term": 20,
        "post_rec_rate": 3, "post_rec_term": 20,
        "incentive_detail": "Smart Inverter Rebate",
        "cust_acq_blend": 0.0334,
    },
    ("IL", "ComEd", "Non-ABP / PTC"): {
        216: 0.25, 217: 3, 161: 0.10, 162: 0.01, 240: 0.00478,
        "rec_rate": 18.5, "rec_term": 10,
        "post_rec_rate": 3, "post_rec_term": "Remaining life",
        "incentive_detail": "Smart Inverter Rebate; Karbone 10-yr strip",
        "cust_acq_blend": 0.0334,
    },

    # ---------------- PA ----------------
    ("PA", "ALL", "PTC"): {
        216: 0.0, 217: 0, 161: 0.0, 162: 0.01, 240: 0.0,
        "rec_rate": 18.5, "rec_term": 10, "post_rec_rate": 3, "post_rec_term": 25,
        "rate_curve": "Trailing 12-month average", "rate_source": "GH (PTC)",
        "cust_acq_blend": 0,
    },

    # ---------------- MN ----------------
    ("MN", "Xcel", "LMI-Accessible CS"): {
        216: 0.0, 217: 0, 161: 0.105, 162: 0.01, 240: 0.00749,
        "rec_rate": 0, "rec_term": 0, "post_rec_rate": 0, "post_rec_term": 0,
        "rate_curve": "Trailing 12-month average", "rate_source": "GH",
        "cust_acq_blend": 0.0599,
    },
}

def normalize_state(state: str | None) -> str:
    """Normalize state for market lookups. MD/DE → 'MD/DE'."""
    if not state:
        return ""
    s = str(state).strip().upper()
    return "MD/DE" if s in ("MD", "DE", "MD/DE") else s


# Pre-built O(1) normalized index: (state, utility_lower, program_lower) → vals
def _build_normalized_index() -> dict[tuple[str, str, str], dict]:
    idx: dict[tuple[str, str, str], dict] = {}
    for (state, util, prog), vals in MARKET_BIBLE.items():
        ns = normalize_state(state)
        key = (ns, util.lower(), prog.lower())
        idx[key] = vals
    return idx


_NORMALIZED_INDEX = _build_normalized_index()

# State → list of (utility, program, vals) for fuzzy fallback
def _build_market_index():
    idx: dict[str, list[tuple[str, str, dict]]] = {}
    for (state, util, prog), vals in MARKET_BIBLE.items():
        ns = normalize_state(state)
        idx.setdefault(ns, []).append((util, prog, vals))
    return idx

MARKET_INDEX = _build_market_index()


def lookup_market(state, utility, program):
    """Return bible dict for (state, utility, program), or None if no match.

    O(1) exact lookup first, then fuzzy fallback on utility/program.
    Tolerant: case-insensitive, strips whitespace, normalizes MD/DE.
    """
    s = normalize_state(state)
    if not s:
        return None
    u = str(utility or "").strip()
    p = str(program or "").strip()

    # O(1) exact normalized lookup
    exact = _NORMALIZED_INDEX.get((s, u.lower(), p.lower()))
    if exact is not None:
        return exact

    # Fuzzy fallback: utility substring match
    candidates = MARKET_INDEX.get(s, [])
    u_low = u.lower()
    p_low = p.lower()
    for util_k, prog_k, vals in candidates:
        uk = util_k.lower()
        pk = prog_k.lower()
        util_match = not u or (uk in u_low) or (u_low in uk)
        prog_match = not p or (pk in p_low) or (p_low in pk)
        if util_match and prog_match:
            return vals

    # State has only one market → return it
    if len(candidates) == 1:
        return candidates[0][2]

    return None
