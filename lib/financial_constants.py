"""Shared financial constants used across review + walk pipelines.

Single source of truth for cashflow horizon, NPV dampener, default yield,
and bible-default eligible-cost fraction. Previously duplicated across
mockup_view.py and impact.py with subtly different values — extracted here
so future updates touch ONE place. Imports stay cheap (no transitive
dependencies on heavy modules).
"""

from __future__ import annotations

#: PPA / OpEx cash-flow horizon in years. Standard 38DN PPA term.
OPEX_TERM_YEARS = 25

#: NPV dampener applied to the 25-year OpEx/revenue stream. Calibrated
#: against the bible's ~7.25% WACC at 25-year tenor — produces sensible
#: present-value magnitudes for sensitivity tornadoes and walk impact rows.
OPEX_NPV_FACTOR = 0.55

#: Fallback project yield (kWh/Wdc/yr) when the model doesn't expose row 14.
#: 1.55 is the community-solar average across 38DN's portfolio.
DEFAULT_YIELD_KWH_PER_WP = 1.55

#: Bible default for ITC-eligible cost fraction (1 - non-eligible items).
#: Used when a model doesn't populate row 602.
BIBLE_ELIG_FRAC = 0.97
