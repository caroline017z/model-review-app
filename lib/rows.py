"""Canonical row numbers in the pricing model's Project Inputs sheet.

The model template places each input at a canonical row. In practice, that row
drifts between versions; `data_loader._build_row_mapping` resolves each
canonical row to its actual position by matching the left-column label
(plus `ROW_LABEL_ALIASES`). Downstream code always keys by the canonical
number below so the mapping layer is the single place that cares about drift.

Keeping every row constant in one module means:
  * `data_loader`, `mockup_view`, `bible_audit`, and `bible_reference` share
    the same source of truth.
  * Adding a new row requires exactly one edit here plus (optionally) an
    alias list in `data_loader.ROW_LABEL_ALIASES`.
"""

# --- Project identity ---------------------------------------------------------
ROW_PROJECT_NUMBER = 2  # Sequential project # used by Returns sheets
ROW_PROJECT_NAME = 4
ROW_TOGGLE = 7  # "On" / "Off"
ROW_38DN_DEV_TOGGLE = 8  # internal 38DN vs third-party
ROW_DEVELOPER = 10  # external developer name

# --- System sizing ------------------------------------------------------------
ROW_DC_MW = 11
ROW_AC_KW = 12
ROW_DC_AC_RATIO = 13
ROW_YIELD_KWH_PER_WDC = 14
ROW_COD_YEAR = 15
ROW_SYSTEM_LIFE = 16
ROW_EFFECTIVE_LIFE = 17

# --- Location & program -------------------------------------------------------
ROW_STATE = 18
ROW_UTILITY = 19
ROW_PROGRAM_A = 22
ROW_PROGRAM_B = 21  # legacy fallback row for program/customer

# --- Financial outputs --------------------------------------------------------
# Row 31: Appraisal IRR (a.k.a. "Live Appraisal IRR") — converges to the
#         FMV WACC target. This is the deal-level IRR an IC reviewer cares about.
# Row 33: FMV $/W ("FMV Calculated") — dollars per watt, NOT an IRR.
# Row 37: Live Levered Pre-Tax IRR — the pre-tax levered return.
# Row 681: Active MFV (on Project Inputs in most models).
ROW_APPRAISAL_IRR = 31  # canonical "Appraisal IRR"
ROW_FMV_IRR = 31  # alias kept for backward compat
ROW_FMV_PER_W = 33
ROW_LEVERED_PT_IRR = 37
ROW_NPP = 38
ROW_NPP_DOLLARS = 39
ROW_ACTIVE_FMV = 681

# --- Property Tax -------------------------------------------------------------
ROW_CUSTOM_PROPTAX_TOGGLE = 291
ROW_PROPERTY_TAX_YR1 = 292
ROW_PROPTAX_ESCALATOR = 293

# --- CapEx --------------------------------------------------------------------
ROW_EPC_WRAPPED = 118  # set to wrapped total by data_loader
ROW_LNTP = 119
ROW_IX = 122
ROW_CLOSING = 123

# --- Revenue ------------------------------------------------------------------
ROW_PPA_RATE = 157
ROW_ESCALATOR = 158

# --- Incentives & taxes -------------------------------------------------------
ROW_UPFRONT = 216
ROW_UPFRONT_LAG = 217
ROW_ITC_PCT = 597
ROW_ELIG_COSTS = 602

# --- OpEx ---------------------------------------------------------------------
ROW_OM_PREV = 225
ROW_OM_CORR = 226
ROW_OM_ESC = 227
ROW_AM_FEE = 230
ROW_AM_ESC = 231
ROW_CUST_MGMT_ESC = 241
ROW_DECOM_PREMIUM = 286
ROW_INSURANCE = 296
ROW_INSURANCE_ESC = 297
ROW_INTERNAL_AM = 302
