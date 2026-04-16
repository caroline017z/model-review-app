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

# =====================================================================
# PRICING BIBLE Q1 2026
# =====================================================================

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
# Display order — controls row sequence in comparison tables
# Rate Comp 1 fields grouped together, then Rate Comp 2 fields, etc.
# Rate component layout in Project Inputs
RATE_COMP_STARTS = [154, 164, 174, 184, 194, 204]
EQUITY_RATE_TOGGLE_START = 147
DEBT_RATE_TOGGLE_START = 403
APPRAISAL_RATE_TOGGLE_START = 515
