"""
38DN Pricing Model Review — Configuration & Reference Data
Pricing Bible Q1 2026, Market Configs, Benchmarks, Row Mappings.
"""

# =====================================================================
# BRAND PALETTE
# =====================================================================

P = {
    "navy": "#050D25", "navy2": "#212B48", "green": "#45A750", "teal": "#518484",
    "blue": "#1D6FA9", "cyan": "#36AFCE", "light_grey": "#E2E7F1",
    "green_bg": "#E2EFDA", "blue_bg": "#E2E7F1", "dark_blue": "#002060",
    "text": "#282828", "red": "#b83230", "warn": "#45A750",
}
PLOTLY_BG = "#f6f7f9"
PLOTLY_GRID = "rgba(5,13,37,0.05)"
CHART_COLORS = [P["green"], P["blue"], P["teal"], P["navy2"], P["cyan"], P["dark_blue"]]


# =====================================================================
# PRICING BIBLE Q1 2026
# =====================================================================

CS_CAPEX = {
    "Closing & Legal":   {"value": 0.06,  "unit": "$/W",    "row": 124, "note": ""},
    "EPC (excl. LNTP)":  {"value": 1.65,  "unit": "$/W",    "row": 118, "note": ">5 MWdc; <5 MWdc = $1.75. PA 10c cheaper than NY. 6+ MW = $1.55 all-in; <4 MW = $1.75 all-in"},
    "LNTP":              {"value": 0.10,  "unit": "$/W",    "row": 119, "note": "4-6 MW standard"},
}

CS_OPEX = {
    "PV O&M Preventative":     {"value": 4750,   "unit": "$/MW/yr", "row": 225, "esc": 0.02, "note": "Up from $4,500 in Q2"},
    "PV O&M Corrective":       {"value": 2000,   "unit": "$/MW/yr", "row": 226, "esc": 0.02, "note": ""},
    "AM for Financing":        {"value": 3000,   "unit": "$/MW/yr", "row": 228, "esc": 0.02, "note": ""},
    "AM - Internally Incurred":{"value": 2500,   "unit": "$/MW/yr", "row": 301, "esc": 0.02, "note": ""},
    "Insurance":               {"value": 3500,   "unit": "$/MW/yr", "row": 296, "esc": 0.02, "note": "Increase to $4,815 for IL (higher hail risk)"},
    "Customer Management":     {"value": None,   "unit": "$/kWh",   "row": 239, "esc": 0.02, "note": "See Market Specific Assumptions. NY: price to S-SFA"},
    "Subscriber Churn":        {"value": 0.0256, "unit": "%",       "row": 245, "esc": None, "note": ""},
    "Decom Bond Premium":      {"value": 0.025,  "unit": "% of bond","row": 281, "esc": 0.02, "note": "If no bond amt: use 1.5% of EPC"},
}

CS_CONSTRUCTION_LOAN = {
    "CL Base Interest Rate":   {"value": 0.0365, "unit": "%", "note": "T6M SOFR = 3.65%"},
    "CL Margin":               {"value": 0.0265, "unit": "%", "note": "Total CL rate ~6.30%"},
    "CL Origination Fee":      {"value": 0.01,   "unit": "% of CapEx", "note": ""},
    "Max CL Advance Rate":     {"value": 0.90,   "unit": "%", "note": "Dependent on Transfer Credit eligibility"},
    "TE Commit Date":          {"value": "NTP+3mos", "unit": "", "note": ""},
}

CS_PERM_DEBT_FRONT = {
    "Loan Tenor":              {"value": 25,     "unit": "years", "note": ""},
    "Base Interest Rate (25yr)":{"value": 0.04995,"unit": "%", "note": "+18.4bps from Q3"},
    "Base Interest Rate (7yr)": {"value": 0.04408,"unit": "%", "note": "-8.2bps from Q3"},
    "Rate Step-Up (7yr only)":  {"value": 0.004,  "unit": "%", "note": ""},
    "Interest Rate Margin":     {"value": 0.022,  "unit": "%", "note": "Total ~7.20% for 25yr"},
    "USDA Project Fee":         {"value": 14500,  "unit": "$", "note": "Fixed"},
    "Structuring Fee (USDA)":   {"value": 0.0105, "unit": "%", "note": ""},
    "Structuring Fee (non-USDA)":{"value": 0.015, "unit": "%", "note": ""},
}

CS_DSCR_FRONT = {"Year 1": 2.00, "Year 2": 1.75, "Year 3": 1.60, "Year 4": 1.60, "Year 5": 1.60, "Year 6+": 1.35}

CS_PERM_DEBT_BACK = {
    "Loan Tenor":              {"value": 7,      "unit": "years", "note": ""},
    "Base Interest Rate":      {"value": 0.0404, "unit": "%", "note": "Lesser of 7yr Treasury T6M + 25bps and current 40bps"},
    "Interest Rate Margin":    {"value": 0.025,  "unit": "%", "note": "IL at 2.75%"},
    "Closing Fee":             {"value": 0.015,  "unit": "%", "note": "IL 1.5%, others 1.0-1.25%"},
}

CS_DSCR_BACK = {"Year 1": 2.00, "Year 2": 1.75, "Year 3": 1.60, "Year 4": 1.60, "Year 5": 1.60,
                "Year 6+ (Fixed Revenue)": 1.30, "Year 6+ (PTC/Retail)": 1.40, "Year 6+ (Wholesale)": 1.75}

CS_TAX_EQUITY = {
    "FMV Step Up Cap":          {"value": 0.30,   "unit": "%", "note": ""},
    "FMV WACC":                 {"value": 0.0725, "unit": "%", "note": "NY = 7.00% (BDO adjusted); IL = 8.00%"},
    "PPC":                      {"value": 1.06,   "unit": "$/ITC", "note": ""},
    "TE Buyout":                {"value": 0.07,   "unit": "%", "note": ""},
    "TE Pref":                  {"value": 0.025,  "unit": "%", "note": ""},
    "IM TE Variable Cash":      {"value": 0.01,   "unit": "%", "note": ""},
    "TE Insurance Coverage":    {"value": 0.035,  "unit": "%", "note": "Full ITC basis. Solcap: 4% on step-up only if PIS in 2026"},
}

CS_EPC_SPEND = {
    "Month 0": 0.00, "Month 1 (NTP+)": 0.15, "Month 2": 0.05, "Month 3": 0.00,
    "Month 4": 0.20, "Month 5": 0.10, "Month 6": 0.10, "Month 7": 0.15,
    "Month 8": 0.05, "Month 9": 0.00, "Month 10": 0.05, "Month 11": 0.10,
    "Month 12": 0.00, "Month 13": 0.00, "Month 14": 0.05,
}

STATE_NOTES = {
    "IL": ["Insurance: $4,815/MW/yr (vs $3,500 standard) due to higher hail risk",
           "FMV WACC: 8.00% (vs 7.25% standard)", "Back leverage margin: 2.75% (vs 2.50%)",
           "Back leverage closing fee: 1.50%", "Rate curves: GH25 with 17.5% discount",
           "Year 6+ DSCR (Fixed): can be 1.40x floor (already discounting rates by 20%)"],
    "NY": ["FMV WACC: 7.00% (BDO adjusted down, vs 7.25% standard)", "Rate curves: 3Q25 TTM",
           "Customer management: price to S-SFA",
           "DRV: 25% IX deposit before July 2026 = Current DRV Y1-10, Staff PSC Y11+",
           "REC rate: $31.03/MWh (25-year, part of VDER stack)"],
    "MD": ["Rate curves: GH25 with 22.5% discount",
           "REC rates: Karbone 10-yr strip (Y1: $43, declining to Y6-10: $18/MWh)",
           "Post-REC rate: $3/MWh", "Property tax: CEH methodology \u2014 2.08% personal, 0.94% real"],
    "PA": ["EPC: ~10 cents cheaper than NY", "No official CS program yet \u2014 PTC structure",
           "Property tax: lease-based valuation, cap rate 8%"],
}


# =====================================================================
# MARKET SPECIFIC ASSUMPTIONS
# =====================================================================

MARKET_CONFIGS = {
    ("NY","National Grid","VDER (CS)"):{"col":"D","upfront_incentive":0.175,"incentive_lag":3,
        "incentive_detail":"MW Block ($0.05) + Prevailing Wage ($0.125)",
        "cust_resi":"S-SFA","cust_comm":"S-SFA","cust_anchor":"S-SFA","cust_lmi":"S-SFA",
        "disc_resi":"S-SFA","disc_comm":"S-SFA","disc_anchor":"S-SFA","disc_lmi":"S-SFA","disc_blend":"S-SFA",
        "cma_blend":0,"ucb":0.015,"rate_curve":"3Q25 TTM","rate_source":"NYGB",
        "rec_rate":31.03,"rec_term":25,"post_rec":0,"post_rec_term":10,"rec_note":"Part of VDER Stack"},
    ("NY","NYSEG","VDER (CS)"):{"col":"E","upfront_incentive":0.175,"incentive_lag":3,
        "incentive_detail":"MW Block ($0.05) + Prevailing Wage ($0.125)",
        "cust_resi":"S-SFA","cust_comm":"S-SFA","cust_anchor":"S-SFA","cust_lmi":"S-SFA",
        "disc_resi":"S-SFA","disc_blend":"S-SFA","cma_blend":0,"ucb":0.015,
        "rate_curve":"3Q25 TTM","rate_source":"NYGB",
        "rec_rate":31.03,"rec_term":25,"post_rec":0,"post_rec_term":10},
    ("NY","Other (Non-NG/NYSEG)","VDER (CS)"):{"col":"F","upfront_incentive":0.175,"incentive_lag":3,
        "incentive_detail":"MW Block ($0.05) + Prevailing Wage ($0.125)",
        "cust_resi":"S-SFA","cust_comm":"S-SFA","cust_anchor":"S-SFA","cust_lmi":"S-SFA",
        "disc_resi":"S-SFA","disc_blend":"S-SFA","cma_blend":0,"ucb":0.015,
        "rate_curve":"3Q25 TTM","rate_source":"NYGB",
        "rec_rate":31.03,"rec_term":25,"post_rec":0,"post_rec_term":10},
    ("MD/DE","Delmarva","MD PILOT"):{"col":"G","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.15,"disc_blend":0.10,
        "cma_blend":0.0069,"ucb":0.01,
        "acq_blend":0.092,"acq_resi":0.092,"acq_comm":0.092,"acq_anchor":0.05,"acq_lmi":0.136,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":10,"post_rec":3,"post_rec_term":30},
    ("MD/DE","Delmarva","MD Permanent"):{"col":"H","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.30,"cust_comm":0.20,"cust_anchor":0,"cust_lmi":0.50,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.30,"disc_blend":0.20,
        "cma_blend":0.0083,"ucb":0.01,
        "acq_blend":0.0739,"rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":5,"post_rec":3,"post_rec_term":30},
    ("MD/DE","Potomac Edison","MD PILOT"):{"col":"I","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.20,"disc_blend":0.10,
        "cma_blend":0.00655,"ucb":0.01,"acq_blend":0.0655,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":10,"post_rec":3,"post_rec_term":30},
    ("MD/DE","Potomac Edison","MD Permanent"):{"col":"J","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.50,"cust_comm":0,"cust_anchor":0,"cust_lmi":0.50,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.20,"disc_blend":0.15,
        "cma_blend":0.0072,"ucb":0.01,"acq_blend":0.0735,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":5,"post_rec":3,"post_rec_term":30},
    ("MD/DE","BGE","MD PILOT"):{"col":"K","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.60,"cust_comm":0.40,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.05,"disc_anchor":0.05,"disc_lmi":0.15,"disc_blend":0.08,
        "cma_blend":0.00672,"ucb":0.01,"acq_blend":0.0666,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":10,"post_rec":3,"post_rec_term":30},
    ("MD/DE","BGE","MD Permanent"):{"col":"L","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.10,"cust_comm":0.40,"cust_anchor":0,"cust_lmi":0.50,
        "disc_resi":0.10,"disc_comm":0.05,"disc_anchor":0.05,"disc_lmi":0.20,"disc_blend":0.13,
        "cma_blend":0.00717,"ucb":0.01,"acq_blend":0.0701,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":5,"post_rec":3,"post_rec_term":30},
    ("MD/DE","PEPCO","MD PILOT"):{"col":"M","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.60,"cust_comm":0.40,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.05,"disc_anchor":0.05,"disc_lmi":0.15,"disc_blend":0.08,
        "cma_blend":0.00682,"ucb":0.01,"acq_blend":0.0666,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":10,"post_rec":3,"post_rec_term":30},
    ("MD/DE","PEPCO","MD Permanent"):{"col":"N","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.30,"cust_comm":0.20,"cust_anchor":0,"cust_lmi":0.50,
        "disc_resi":0.10,"disc_comm":0.05,"disc_anchor":0.05,"disc_lmi":0.30,"disc_blend":0.19,
        "cma_blend":0.00741,"ucb":0.01,"acq_blend":0.0713,
        "rate_curve":"GH25 | 22.5% discount","rate_source":"GH",
        "rec_rate":"Y1-5: $43/33/31/26/21; Y6-10: $18","rec_term":5,"post_rec":3,"post_rec_term":30},
    ("IL","Ameren","ABP"):{"col":"O","upfront_incentive":0.25,"incentive_lag":3,
        "incentive_detail":"Smart Inverter Rebate",
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.15,"disc_blend":0.10,
        "cma_blend":0.0049,"ucb":0.01,
        "acq_blend":0.0366,"acq_resi":0.0442,"acq_comm":0.0289,
        "rate_curve":"GH25 | 17.5% discount","rate_source":"GH",
        "rec_rate":"Project Dependent","rec_term":20,"post_rec":3,"post_rec_term":20},
    ("IL","Ameren","Non-ABP / PTC"):{"col":"P","upfront_incentive":0.25,"incentive_lag":3,
        "incentive_detail":"Smart Inverter Rebate",
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.15,"disc_blend":0.10,
        "cma_blend":0.0049,"ucb":0.01,"acq_blend":0.0366,
        "rate_curve":"GH25 | 17.5% discount","rate_source":"GH",
        "rec_rate":3,"rec_term":"Full project life","post_rec":3,"post_rec_term":"Remaining project life"},
    ("IL","ComEd","ABP"):{"col":"Q","upfront_incentive":0.25,"incentive_lag":3,
        "incentive_detail":"Smart Inverter Rebate",
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.15,"disc_blend":0.10,
        "cma_blend":0.00478,"ucb":0.01,"acq_blend":0.0334,
        "rate_curve":"GH25 | 17.5% discount","rate_source":"GH",
        "rec_rate":"Project Dependent","rec_term":20,"post_rec":3,"post_rec_term":20},
    ("IL","ComEd","Non-ABP / PTC"):{"col":"R","upfront_incentive":0.25,"incentive_lag":3,
        "incentive_detail":"Smart Inverter Rebate",
        "cust_resi":0.50,"cust_comm":0.50,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.15,"disc_blend":0.10,
        "cma_blend":0.00478,"ucb":0.01,"acq_blend":0.0334,
        "rate_curve":"GH25 | 17.5% discount","rate_source":"GH",
        "rec_rate":18.5,"rec_term":10,"post_rec":3,"post_rec_term":"Remaining project life",
        "rec_note":"Karbone 10-year strip"},
    ("PA","ALL","PTC"):{"col":"S","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0,"cust_comm":0,"cust_anchor":0,"cust_lmi":0,
        "disc_resi":0,"disc_comm":0,"disc_anchor":0,"disc_lmi":0,"disc_blend":0,
        "cma_blend":0,"ucb":0.01,"acq_blend":0,
        "rate_curve":"Trailing 12-month average","rate_source":"GH (PTC)",
        "rec_rate":18.5,"rec_term":10,"post_rec":3,"post_rec_term":25},
    ("MN","Xcel","LMI-Accessible CS"):{"col":"T","upfront_incentive":0,"incentive_lag":0,
        "cust_resi":0.45,"cust_comm":0,"cust_anchor":0,"cust_lmi":0.60,
        "disc_resi":0.10,"disc_comm":0.10,"disc_anchor":0.10,"disc_lmi":0.10,"disc_blend":0.105,
        "cma_blend":0.00749,"ucb":0.01,"acq_blend":0.0599,
        "rate_curve":"Trailing 12-month average","rate_source":"GH",
        "rec_rate":0,"rec_term":0,"post_rec":0,"post_rec_term":0},
}

MARKET_HIERARCHY = {}
for (state, util, prog) in MARKET_CONFIGS:
    MARKET_HIERARCHY.setdefault(state, {}).setdefault(util, []).append(prog)


# =====================================================================
# VALIDATION BENCHMARKS
# =====================================================================

BIBLE_BENCHMARKS = {
    "CapEx": {
        "EPC Cost ($/W)":        {"row": 118, "min": 1.55, "max": 1.75, "unit": "$/W"},
        "LNTP Cost ($/W)":       {"row": 119, "min": 0.08, "max": 0.12, "unit": "$/W"},
        "IX Cost ($/W)":         {"row": 122, "min": 0.00, "max": 0.50, "unit": "$/W"},
        "Cust Acquisition ($/W)":{"row": 121, "min": 0.00, "max": 0.20, "unit": "$/W"},
        "Closing & Legal ($/W)": {"row": 123, "min": 0.05, "max": 0.075, "unit": "$/W"},
        "ESS EPC Cost ($/kWh)":  {"row": 126, "min": 0.00, "max": 500.0, "unit": "$/kWh"},
    },
    "System Sizing": {
        "Size MWDC":             {"row": 11,  "min": 0.1,  "max": 100.0, "unit": "MWdc"},
        "Size MWAC":             {"row": 12,  "min": 0.1,  "max": 100.0, "unit": "MWac"},
        "DC:AC Ratio":           {"derived": True, "num_row": 11, "den_row": 12, "min": 1.10, "max": 2.10, "unit": "ratio"},
        "Energy Yield (kWh/MWp)":{"row": 14,  "min": 1.200, "max": 2.000, "unit": "kWh/MWp"},
    },
    "Revenue": {
        "PPA Rate ($/kWh)":      {"row": 157, "min": 0.03,  "max": 0.20,  "unit": "$/kWh"},
        "Escalator (%)":         {"row": 158, "min": 0.005, "max": 0.035, "unit": "%"},
        "Rate Term (yrs)":       {"row": 160, "min": 15,    "max": 40,    "unit": "years"},
        "Revenue Lag (months)":  {"row": 143, "min": 0,     "max": 3,     "unit": "months"},
    },
    "Incentives & Tax": {
        "Upfront Incentive ($/W)": {"row": 216, "min": 0.00, "max": 1.00, "unit": "$/W"},
        "ITC Rate (%)":            {"row": 597, "min": 0.20, "max": 0.50, "unit": "%"},
        "Eligible Costs (%)":      {"row": 602, "min": 0.80, "max": 1.00, "unit": "%"},
    },
    "System Details": {
        "COD Year":              {"row": 15,  "min": 2025,  "max": 2030,  "unit": "year"},
        "System Life (yrs)":     {"row": 16,  "min": 20,    "max": 40,    "unit": "years"},
    },
}


# =====================================================================
# ROW MAPPINGS
# =====================================================================

OUTPUT_ROWS = {38: "NPP ($/W)", 39: "NPP ($)", 33: "FMV Calculated ($/W)"}

INPUT_ROW_LABELS = {
    4: "Project Name", 7: "Toggle (On/Off)", 8: "Developer Toggle",
    10: "Developer", 11: "Size MWDC", 12: "Size MWAC", 13: "DC-AC Ratio",
    14: "Energy Yield (kWh/WDC)", 15: "Year COD", 16: "System Life",
    17: "Effective System Life", 18: "State", 19: "Utility",
    21: "System Type", 22: "Customer",
    23: "Battery Storage", 24: "BESS Capacity kWac", 25: "BESS Capacity kWh",
    30: "FMV WACC (Target)", 31: "Live Appraisal IRR", 36: "Target IRR", 37: "Live Levered Pre-Tax IRR",
    68: "MIPA Signing", 69: "Close", 70: "NTP", 71: "MC", 72: "COD/PIS", 73: "SC",
    76: "MIPA->Close (mo)", 77: "Close->NTP (mo)", 78: "NTP->MC (mo)", 80: "COD->SC (mo)",
    117: "EPC Spend Curve", 118: "PV EPC Cost", 119: "PV LNTP Cost",
    120: "PV EPC + LNTP Cost",
    121: "Customer Acquisition", 122: "IX Cost",
    123: "Closing and Legal", 124: "Other Capex Costs", 126: "ESS EPC Cost",
    129: "Total Capex Excl. Financing",
    143: "Revenue Lag", 147: "Rate Comp 1", 148: "Rate Comp 2",
    155: "Rate Name", 156: "Custom/Generic",
    157: "Energy Rate (at COD)", 158: "Energy Rate Escalator",
    160: "Rate Term", 161: "Rate Discount", 162: "Rate UCB Fee",
    165: "Rate 2 Name", 166: "Rate 2 Custom/Generic",
    167: "Rate 2 Energy Rate", 168: "Rate 2 Escalator", 170: "Rate 2 Term",
    216: "Upfront Incentive", 217: "Upfront Incentive Lag", 218: "ICSA Incentive",
    219: "ICSA COD %", 220: "ICSA Yr 1 %", 221: "ICSA Yr 2 %",
    225: "PV O&M Preventative", 226: "PV O&M Corrective", 227: "PV O&M Esc",
    228: "ESS O&M", 230: "AM Fee", 231: "AM Esc",
    234: "Upfront Bonus Lease", 235: "Lease Term", 236: "Lease (Year 1)", 237: "Lease Escalator",
    240: "Customer Mgmt Cost", 241: "Customer Mgmt Esc",
    255: "Inverter Replacement Toggle", 256: "Inverter Replacement $/MWac", 258: "Inverter Replacement Year",
    282: "Decom Disposal Cost %", 283: "Decom Cost Inflation", 284: "Decom End of Life",
    285: "Decom Bond $", 286: "Decom Annual Premium",
    291: "Custom PropTax Toggle", 292: "Property Taxes Yr 1", 293: "PropTax Escalator",
    296: "P&C Insurance", 297: "P&C Insurance Esc",
    298: "Catastrophic Coverage", 299: "Catastrophic Esc",
    302: "Internal AM Costs",
    587: "COD Quarter",
    591: "Tax Treatment", 596: "TE Structure", 597: "ITC Rate", 602: "Eligible Costs %",
}

PCT_ROWS = {30, 31, 36, 37, 158, 161, 162, 168, 219, 220, 221, 227, 229, 231,
            237, 241, 282, 283, 286, 288, 293, 297, 299, 597, 602}
TEXT_ROWS = {4, 8, 10, 18, 19, 21, 22, 117, 155, 156,
             165, 166, 591, 596}
DATE_ROWS = {68, 69, 70, 71, 72, 73}
# $/W rows — 3 decimal places (e.g. $1.650/W)
DPW_ROWS = {32, 33, 38, 118, 119, 120, 121, 122, 123, 124, 126, 129, 157, 167, 216, 218}
# Integer / dollar rows — no decimals (e.g. $3,500/MW/yr, 2027, 25 kWac)
INT_ROWS = {15, 16, 17, 24, 25, 143, 160, 170, 217, 225, 226, 228, 230, 235,
            240, 256, 258, 284, 285, 292, 296, 298, 302}
NUMERIC_WEIGHT_ROWS = {11, 12, 13, 14, 15, 16, 17, 24, 25, 30, 31, 32, 33, 36, 37, 38, 39,
                       118, 119, 120, 121, 122, 123, 124, 126, 129,
                       143, 157, 158, 160, 161, 162, 167, 168, 170,
                       216, 217, 218, 225, 226, 230, 240, 256, 258,
                       282, 284, 292, 296, 298, 302, 597, 602}

# Display order — controls row sequence in comparison tables
# Rate Comp 1 fields grouped together, then Rate Comp 2 fields, etc.
DISPLAY_ORDER = [
    # Project Details
    4, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25,
    30, 31, 36, 37,
    # Milestones
    68, 69, 70, 71, 72, 73, 76, 77, 78, 80,
    # CapEx
    117, 118, 119, 120, 121, 122, 123, 124, 126, 129,
    # Revenue
    143,
    # Rate Component 1
    147, 155, 156, 157, 158, 160, 161, 162,
    # Rate Component 2
    148, 165, 166, 167, 168, 170,
    # Incentives
    216, 217, 218, 219, 220, 221,
    # OpEx
    225, 226, 227, 228, 230, 231,
    234, 235, 236, 237,
    240, 241,
    255, 256, 258,
    # Decom
    282, 283, 284, 285, 286,
    # Prop Tax & Insurance
    291, 292, 293, 296, 297, 298, 299,
    302,
    # Tax
    587, 591, 596, 597, 602,
    # Outputs
    32, 33, 38, 39,
]

SECTION_BREAKS = {
    4: "Project Details", 68: "Milestones",
    118: "CapEx", 143: "Revenue",
    147: "Rate Component 1", 148: "Rate Component 2",
    216: "Incentives", 225: "OpEx",
    282: "Decommissioning", 291: "Property Tax & Insurance",
    587: "Tax & Depreciation",
    32: "Outputs",
}

# Rate component layout in Project Inputs
RATE_COMP_STARTS = [154, 164, 174, 184, 194, 204]
RATE_FIELDS = {0: "Section", 1: "Rate Name", 2: "Custom/Generic", 3: "Energy Rate ($/kWh)",
               4: "Escalator (%)", 5: "Start Date", 6: "Term (yrs)", 7: "Discount (%)", 8: "UCB Fee (%)"}
EQUITY_RATE_TOGGLE_START = 147
DEBT_RATE_TOGGLE_START = 403
APPRAISAL_RATE_TOGGLE_START = 515
