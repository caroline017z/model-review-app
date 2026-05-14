"""Bible: versioned record of all audit reference data.

A `Bible` instance holds every value the audit pipeline needs to compare
a project against:

  - cs_average           — cross-market exact-match specs (per model row)
  - cs_state_overrides   — per-state CS_AVERAGE substitutions
  - market_bible         — (state, utility, program) → row → value
  - bible_benchmarks     — range checks (BIBLE_BENCHMARKS)
  - cs_tax_equity / cs_perm_debt_* / cs_construction_loan — informational

Plus metadata for replay:
  - vintage_id, label, source, uploaded_at

Why this exists
---------------
Phase 4 of the upgrade plan replaces module-level Python literals with a
runtime-loaded record so Caroline can upload an updated Excel without
editing source. The bundled vintage (`Bible.bundled_q1_2026`) wraps the
current literals so the audit engine produces byte-identical output until
a new vintage is uploaded.

Lookup performance
------------------
Market lookups are O(1) via cached normalized indexes. Indexes are built
lazily on first access via `functools.cached_property`, so vintages
copied/passed around don't pay an upfront indexing cost.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from typing import Any


def _normalize_state(state: Any) -> str:
    """Normalize a state label for market lookups. MD/DE collapse → 'MD/DE'."""
    if not state:
        return ""
    s = str(state).strip().upper()
    return "MD/DE" if s in ("MD", "DE", "MD/DE") else s


# Program aliases: common model labels → MARKET_BIBLE program keys.
# Kept module-level so it's static (unchanging across vintages).
PROGRAM_ALIASES: dict[str, list[str]] = {
    "community": ["ABP", "Non-ABP / PTC", "MD Permanent", "MD PILOT"],
    "community solar": ["ABP", "Non-ABP / PTC", "MD Permanent"],
    "cs": ["ABP", "Non-ABP / PTC"],
    "vder": ["VDER (CS)"],
    "vder (cs)": ["VDER (CS)"],
    "ptc": ["PTC", "Non-ABP / PTC"],
    "abp": ["ABP"],
    "lmi": ["LMI-Accessible CS"],
}


@dataclass
class Bible:
    """A versioned record of all audit reference data.

    Two construction paths:
      - `Bible.bundled_q1_2026()` — wraps the current Python literals
      - `Bible.from_excel(path, label)` — parses a Pricing Bible xlsx
        (see lib/bible_loader.py)

    Equality is by vintage_id alone (snapshots compare structurally).
    """

    vintage_id: str
    label: str
    source: str  # "bundled" or the uploaded filename
    uploaded_at: str  # ISO datetime UTC

    # Audit-critical data (consumed by rules)
    cs_average: dict[int, dict[str, Any]]
    cs_state_overrides: dict[str, dict[int, dict[str, Any]]]
    market_bible: dict[tuple[str, str, str], dict[Any, Any]]
    bible_benchmarks: dict[str, dict[str, dict[str, Any]]]

    # Informational sections (not consumed by audit rules; surfaced for
    # IC narrative + reference panels)
    cs_tax_equity: dict[str, Any] = field(default_factory=dict)
    cs_perm_debt_front: dict[str, Any] = field(default_factory=dict)
    cs_perm_debt_back: dict[str, Any] = field(default_factory=dict)
    cs_construction_loan: dict[str, Any] = field(default_factory=dict)
    cs_epc_spend_curve: dict[str, float] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Indexes (computed lazily; safe to read from concurrent callers
    # because cached_property memoizes per-instance)
    # ------------------------------------------------------------------

    @cached_property
    def _normalized_index(self) -> dict[tuple[str, str, str], dict[Any, Any]]:
        idx: dict[tuple[str, str, str], dict[Any, Any]] = {}
        for (state, util, prog), vals in self.market_bible.items():
            ns = _normalize_state(state)
            idx[(ns, util.lower(), prog.lower())] = vals
        return idx

    @cached_property
    def _market_index(self) -> dict[str, list[tuple[str, str, dict[Any, Any]]]]:
        idx: dict[str, list[tuple[str, str, dict[Any, Any]]]] = {}
        for (state, util, prog), vals in self.market_bible.items():
            ns = _normalize_state(state)
            idx.setdefault(ns, []).append((util, prog, vals))
        return idx

    # ------------------------------------------------------------------
    # Public lookups
    # ------------------------------------------------------------------

    def lookup_market(self, state: Any, utility: Any, program: Any) -> dict[Any, Any] | None:
        """Return bible dict for (state, utility, program), or None.

        Mirrors `lib.bible_reference.lookup_market` byte-for-byte:
        O(1) exact normalized lookup first, then program aliases, then
        fuzzy fallback (utility substring match), then single-market
        fallback when no program specified.
        """
        s = _normalize_state(state)
        if not s:
            return None
        u = str(utility or "").strip()
        p = str(program or "").strip()

        # O(1) exact normalized lookup
        exact = self._normalized_index.get((s, u.lower(), p.lower()))
        if exact is not None:
            return exact

        # Try program aliases (e.g., "Community" → "ABP" for IL)
        aliases = PROGRAM_ALIASES.get(p.lower(), [])
        for alias in aliases:
            aliased = self._normalized_index.get((s, u.lower(), alias.lower()))
            if aliased is not None:
                return aliased

        # Fuzzy fallback: utility substring match
        candidates = self._market_index.get(s, [])
        u_low = u.lower()
        p_low = p.lower()
        for util_k, prog_k, vals in candidates:
            uk = util_k.lower()
            pk = prog_k.lower()
            util_match = not u or (uk in u_low) or (u_low in uk)
            prog_match = not p or (pk in p_low) or (p_low in pk)
            if util_match and prog_match:
                return vals

        # State has only one market → return it ONLY if no specific program
        # was requested (prevents cross-contamination)
        if len(candidates) == 1 and not p:
            return candidates[0][2]

        return None

    def state_override_for(self, state: str | None, row: int) -> dict[str, Any] | None:
        """The (per-state) CS_AVERAGE override entry for a row, if any."""
        if state is None:
            return None
        return self.cs_state_overrides.get(state, {}).get(row)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def bundled_q1_2026(cls) -> Bible:
        """Build a Bible from the current `lib.bible_reference` literals.

        This is the backward-compat bundle: audits run against this when
        no user-uploaded vintage is active. Output is byte-identical to
        the pre-Phase-4 audit pipeline (proved by golden snapshots).
        """
        # Local import to avoid a top-level cycle at module-load time.
        from lib.bible_reference import (
            CS_AVERAGE,
            CS_CONSTRUCTION_LOAN,
            CS_EPC_SPEND_CURVE,
            CS_PERM_DEBT_BACK,
            CS_PERM_DEBT_FRONT,
            CS_STATE_OVERRIDES,
            CS_TAX_EQUITY,
            MARKET_BIBLE,
        )
        from lib.config import BIBLE_BENCHMARKS

        return cls(
            vintage_id="bundled-q1-2026",
            label="Q1 '26 Average (bundled)",
            source="bundled",
            uploaded_at="2026-01-01T00:00:00+00:00",
            # Defensive copies so a caller mutating .cs_average doesn't
            # spook the module-level literals.
            cs_average=copy.deepcopy(CS_AVERAGE),
            cs_state_overrides=copy.deepcopy(CS_STATE_OVERRIDES),
            market_bible=copy.deepcopy(MARKET_BIBLE),
            bible_benchmarks=copy.deepcopy(BIBLE_BENCHMARKS),
            cs_tax_equity=copy.deepcopy(CS_TAX_EQUITY),
            cs_perm_debt_front=copy.deepcopy(CS_PERM_DEBT_FRONT),
            cs_perm_debt_back=copy.deepcopy(CS_PERM_DEBT_BACK),
            cs_construction_loan=copy.deepcopy(CS_CONSTRUCTION_LOAN),
            cs_epc_spend_curve=copy.deepcopy(CS_EPC_SPEND_CURVE),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage / API responses.

        Tuple keys in `market_bible` are flattened to `"state||util||prog"`
        strings so the dict is JSON-friendly. `from_dict` reverses this.
        """
        return {
            "vintage_id": self.vintage_id,
            "label": self.label,
            "source": self.source,
            "uploaded_at": self.uploaded_at,
            "cs_average": _stringify_int_keys(self.cs_average),
            "cs_state_overrides": {
                state: _stringify_int_keys(rows) for state, rows in self.cs_state_overrides.items()
            },
            "market_bible": {
                "||".join((s, u, p)): _stringify_int_keys(vals)
                for (s, u, p), vals in self.market_bible.items()
            },
            "bible_benchmarks": self.bible_benchmarks,
            "cs_tax_equity": self.cs_tax_equity,
            "cs_perm_debt_front": self.cs_perm_debt_front,
            "cs_perm_debt_back": self.cs_perm_debt_back,
            "cs_construction_loan": self.cs_construction_loan,
            "cs_epc_spend_curve": self.cs_epc_spend_curve,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Bible:
        """Inverse of `to_dict`. Restores int row-keys and tuple market keys."""
        market_bible: dict[tuple[str, str, str], dict[Any, Any]] = {}
        for k, vals in data.get("market_bible", {}).items():
            parts = k.split("||")
            if len(parts) != 3:
                continue
            market_bible[(parts[0], parts[1], parts[2])] = _intify_int_keys(vals)

        return cls(
            vintage_id=data["vintage_id"],
            label=data["label"],
            source=data["source"],
            uploaded_at=data["uploaded_at"],
            cs_average=_intify_int_keys(data.get("cs_average", {})),
            cs_state_overrides={
                state: _intify_int_keys(rows)
                for state, rows in data.get("cs_state_overrides", {}).items()
            },
            market_bible=market_bible,
            bible_benchmarks=data.get("bible_benchmarks", {}),
            cs_tax_equity=data.get("cs_tax_equity", {}),
            cs_perm_debt_front=data.get("cs_perm_debt_front", {}),
            cs_perm_debt_back=data.get("cs_perm_debt_back", {}),
            cs_construction_loan=data.get("cs_construction_loan", {}),
            cs_epc_spend_curve=data.get("cs_epc_spend_curve", {}),
        )


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


def _stringify_int_keys(d: dict[Any, Any]) -> dict[str, Any]:
    """Convert int dict keys to str for JSON. Non-int keys pass through."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        out[str(k) if isinstance(k, int) else k] = v
    return out


def _intify_int_keys(d: dict[Any, Any]) -> dict[Any, Any]:
    """Convert string-numeric keys back to int (inverse of stringify)."""
    out: dict[Any, Any] = {}
    for k, v in d.items():
        if isinstance(k, str) and k.lstrip("-").isdigit():
            out[int(k)] = v
        else:
            out[k] = v
    return out


def vintage_id_from_upload(filename: str | None = None) -> str:
    """Generate a vintage id for a user-uploaded bible.

    Format: `upload-YYYYMMDDTHHMMSSZ`. Caller can pass the filename for
    display but the ID is purely time-based for collision avoidance.
    """
    _ = filename  # filename intentionally unused — kept for future use
    return "upload-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
