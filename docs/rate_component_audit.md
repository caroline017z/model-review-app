# Revenue Rate-Component Coverage Audit

The Pricing Model Review tool runs a three-model coverage audit over the six Revenue Rate Components (RC1–RC6) in every uploaded 38DN DevEngine workbook. This document captures **what the audit checks, why it exists, and how the data flows** from the workbook into the audit output.

## Why

Pricing busts in revenue config are not visible at the live-pull layer of the model. They sit one level down — in the per-RC sub-blocks in Project Inputs and in the debt/appraisal override blocks — and produce realistic-looking NPP solutions that quietly miss or double-count revenue.

**Documented precedent:** the **CI Renewables Belfast 1 → Forest Hill Presbyterian walk (2026-05-14)** found that Belfast 1's pricing model carried two undocumented busts:

- **Revenue Rate Component 5 was running through the equity model** when it shouldn't have been.
- **Revenue Rate Component 1's term was set to 25 years instead of 30** (system life was 30).

Combined, these inflated Belfast 1's NPP by **~$0.90/W**. The first walk through the project missed both because no audit step compared the RC config across the equity, debt, and appraisal models. This audit closes that gap.

## What the audit checks

For every rate component slot (RC1–RC6) in every project column of an uploaded workbook, the audit produces a finding with status `OK`, `REVIEW`, or `OFF`. Issue strings are attached to non-OK findings.

The audit flags:

1. **Term shorter than system life.** When a rate component is active on the equity model and its term length (`Project Inputs` sub-block, offset +6 from each RC's start row) runs more than 0.5 years short of system life (`Project Inputs` row 16), the component is flagged `OFF`. This catches Belfast's RC1=25yr against a 30yr system life.

2. **Atypical slot active.** RC5 and RC6 are dormant on most community-solar deals. When either is active on the equity model, the audit emits a `REVIEW` finding so a reviewer can confirm the intended revenue mechanism. Some deals legitimately use them; Belfast 1's RC5 was a documented bust.

3. **Active-state divergence across models.** When the master `"Match Debt Revenue to Equity?"` toggle is **OFF** (the debt-side override block governs CFADS), the audit compares each RC's equity toggle against its debt toggle. The same comparison runs for the appraisal model gated by `"Match Appraisal to Equity?"`. Divergence flags `OFF`. When the master toggle is ON, the override block is dormant and the audit suppresses the divergence check.

4. **Active component missing critical fields.** An equity-active RC with a blank name, or an equity-active Generic-mode RC with a blank Energy Rate at COD, flags `OFF` as a data-quality issue.

The audit also surfaces both master `Match` toggle states verbatim so a reviewer can see at a glance whether the debt and appraisal models are mirroring equity or running on overrides.

## Data flow

The audit composes two layers:

| Layer | Module | Responsibility |
|---|---|---|
| Extraction | `lib/data_loader.py` | `_scan_rate_components` reads each RC's name, energy_rate, discount, and three per-model toggles. The per-project loop reads the full sub-block (including term, escalator, start date, custom/generic toggle, UCB fee) and the two master Match toggles at rows 400 and 512. All RC-level state is exposed on the project's `data` dict as `_rate_comps`, `_debt_match_equity`, and `_appraisal_match_equity`. |
| Audit | `lib/bible_audit.py` | `_audit_rc_coverage` consumes those keys plus `ROW_SYSTEM_LIFE` (row 16) and returns a list of per-RC finding dicts. `audit_project` attaches the result as `rc_coverage` and the resolved Match toggles as `rc_match_toggles` on the audit return dict, alongside the existing `rows` / `guidehouse` / `wrapped_epc` blocks. |

### Row anchors in the current template

The on-disk template that the audit was calibrated against (master, 2026-05) uses:

| Constant | Value | Where |
|---|---|---|
| `RATE_COMP_STARTS` | `[154, 164, 174, 184, 194, 204]` | `lib/config.py` |
| `EQUITY_RATE_TOGGLE_START` | `147` (RC1 at 147, RC6 at 152) | `lib/config.py` |
| `DEBT_RATE_TOGGLE_START` | `403` (RC1 at 403, RC6 at 408) | `lib/config.py` |
| `APPRAISAL_RATE_TOGGLE_START` | `515` (RC1 at 515, RC6 at 520) | `lib/config.py` |
| `_debt_match_equity` row | `400` | hardcoded in `data_loader.py` |
| `_appraisal_match_equity` row | `512` | hardcoded in `data_loader.py` |
| `ROW_SYSTEM_LIFE` | `16` | `lib/rows.py` |
| Sub-block field offsets | `+1` name, `+2` custom/generic, `+3` energy_rate, `+4` escalator, `+5` start_date, `+6` term, `+7` discount, `+8` UCB fee | `data_loader.py` per-project loop |

These row addresses are **template-stable across the model versions covered by the current calibration set** (RP Puma, IL US Solar). If a future template revision moves them, update the constants and add a label-based fallback similar to `_build_row_mapping` for the rest of the inputs.

## Audit output shape

`audit_project()` returns the existing dict plus two new top-level keys:

```python
{
    "rows": {...},               # existing per-row Bible findings
    "guidehouse": [...],          # existing Guidehouse discount audit
    "wrapped_epc": {...},         # existing wrapped-EPC build-up
    "summary": {...},

    # New in feature/rc-coverage-audit:
    "rc_coverage": [
        {
            "idx": 1,
            "name": "GH25 Energy",
            "equity_on": True, "debt_on": True, "appraisal_on": True,
            "term": 25.0,
            "system_life": 30.0,
            "status": "OFF",
            "issues": [
                "Term 25yr is 5yr shorter than system life 30yr - revenue gap",
            ],
        },
        ...
    ],
    "rc_match_toggles": {
        "debt_match_equity": True,
        "appraisal_match_equity": True,
        "debt_match_raw": "Yes",
        "appraisal_match_raw": "Yes",
    },
}
```

UI surfaces (FastAPI `/review`, `/walk`) inherit these keys automatically through the existing `audit_project` → `audit_projects` orchestration; they pass through as JSON without explicit serialization changes.

## Future work

- **Three-model term comparison.** Today the term-shortfall check runs on the equity-side term only. The debt and appraisal override blocks have their own RC term cells that the audit does not yet read. When the master Match toggle is OFF the override block governs but we currently can't verify its term length against system life. Capturing override-block terms in `_scan_rate_components` and adding the cross-model comparison closes that gap.

- **Per-deal allow-listing for RC5/RC6.** If a deal legitimately uses RC5 (e.g., a state-specific incentive), the `REVIEW` status will keep firing. A reviewer-side suppress mechanism (per-project annotation in the Bible vintage) would let the audit pass cleanly on those deals.

- **Walk-comparison surfacing.** The `/walk` route compares two models row-by-row but does not yet compare their `rc_coverage` outputs side-by-side. Adding a delta view ("RC5 ON on M1, OFF on M2") would catch the Belfast pattern at the walk stage, not just at single-model upload.

## References

- Memory: `feedback_revenue_component_audit.md` — the rule, Belfast incident, and audit recipe
- Caroline's Code memory: `project_walk_workflow.md` — mandatory Step-0 RC audit before walk-plan classification
- Deep map: `Claude-Work/About-Me/devengine-model-deep-map.md` §4 — RC sub-block field offsets and the three-model audit checklist
- Slim map: `Claude-Work/About-Me/devengine-model-map.md` §5 — RC coverage audit as a High-Stakes Guardrail
