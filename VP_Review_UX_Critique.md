# VP Review App — UX & Analytical Critique

**Reviewer perspective:** Investor-grade IC review tool for solar/BESS portfolio acquisitions. Built for a VP/Director walking into a deal review needing to (a) form a fast point-of-view, (b) trust the inputs, (c) defend the recommendation. The current build has the *data plumbing* right — bible audit, mapper cross-ref, range checks all wire through correctly — but the *surfacing* is still a power-user inspection tool, not an IC narrative tool.

---

## 1. Information architecture

**Current state.** Seven peer tabs (Portfolio, Bible, Market, Comparison, Review, Value Drivers, Raw Data). They're flat, equally weighted, and ordered by build sequence rather than by review workflow. A reviewer opening the app for the first time has no signal as to where to start, and a returning reviewer has to mentally rebuild the path on every session.

**Problem.** IC review is a funnel — *portfolio health → exception triage → individual deal deep-dive → recommendation*. The current tab order forces lateral browsing. Audit findings, the single highest-signal output of the tool, are buried inline inside Comparison rather than promoted to a first-class surface.

**Recommendation.**

- Collapse to **three workspace modes**, selectable via a top segmented control rather than tabs: **Portfolio**, **Project Deep-Dive**, **Reference**.
- Inside Portfolio: the landing view is an **exception ledger** — every project, every audit-OFF/OUT/MISSING finding, sortable by severity and $-impact. Bible audit becomes the headline, not a footnote.
- Inside Project Deep-Dive: a single project at a time, three stacked panels — *Header & verdict* / *Findings & comparison* / *Drivers & sensitivity*. No tab-switching to assemble a narrative.
- Reference becomes a thin sidebar drawer, not a tab — Bible and Market tables are lookups, not destinations.

---

## 2. Visual hierarchy & density

**Current state.** Dense by design (good — financial review demands density), but density without a clear *primary signal* per screen. KPI cards are uniformly sized regardless of whether they carry decision-relevant content. The audit highlight is a 3px inset bar inside a comparison cell — easy to miss when scanning a 50-row table.

**Recommendation.**

- Establish a clear *primary / secondary / tertiary* type scale and stop using the same KPI card visual weight for "Project Count" as for "Audit Findings". Findings should dominate.
- Promote audit-OFF cells with a stronger background tint and a leading icon glyph in the field-label column ("●") so the reviewer can scan vertically without reading every cell.
- Reserve red strictly for hard exceptions ($-impact OFF). Yellow for OUT-of-range. Grey for MISSING. Blue for REVIEW. Today the green KPI border is overused — drop semantic green except for explicit pass states.

---

## 3. Audit / exception surfacing

**Current state.** Audit results are computed per project but only revealed when the user navigates to Comparison and hovers individual cells. There's no portfolio-wide rollup ("Portfolio has 47 OFF findings totalling $X equity impact"). The hover tooltip is the only place the bible expected value is shown next to the actual.

**Recommendation.**

- **Portfolio audit summary strip** at the top of every view: `47 OFF · 12 OUT · 8 MISSING · 3 REVIEW`, each clickable to filter the project list.
- **Findings table** as a first-class artifact with columns: Project / Field / Bible / Actual / Δ / $-impact estimate / Source / Note. Sortable, exportable, with a "mark as accepted variance" toggle so the reviewer can sign off on intentional deviations and have them suppressed on the next pass.
- **Inline finding chips** in the project header — `EPC OFF · ITC OFF · Upfront OUT` — so the deal verdict is visible before scrolling into details.
- **Δ$ quantification.** The current audit knows expected vs actual but doesn't translate to dollar impact. A simple per-row $-multiplier (kW × Δ$/W for EPC; kWh × Δ$/kWh for opex; etc.) turns "EPC is $0.43 off" into "≈ $213k under-budgeted on this project" — this is the number the reviewer actually needs.

---

## 4. Cross-project / portfolio view

**Current state.** Portfolio tab exists but is mostly a project list. There's no way to see, at a glance, which projects are bible-clean vs which are heavily flagged, no way to compare the *same* metric across the portfolio, and no way to spot patterns ("all IL Ameren Community projects are missing the Smart Inverter Rebate").

**Recommendation.**

- **Heatmap matrix:** rows = projects, columns = key bible fields (EPC, LNTP, ITC, Upfront, Insurance, OpEx, etc.), cell color = audit status. One screen, complete portfolio audit posture.
- **Field-level distribution chart.** For each bible-tracked field, show the portfolio distribution as a strip plot with the bible value as a vertical reference line — instant visual on systematic vs idiosyncratic deviations.
- **Group-by filters:** state, utility, program, developer. Lets the reviewer ask "show me everything Lightstar in IL ABP" in one click.

---

## 5. Status communication & trust signals

**Current state.** Audit status uses 5 levels (OK/OFF/OUT/MISSING/REVIEW) — good granularity — but no severity weighting and no "this finding has been reviewed" state. The reviewer can't tell if a finding is new since last open.

**Recommendation.**

- Add **severity** (low / med / high) driven by $-impact, not by status type alone. A $200 OpEx delta and a $0.40/W EPC delta shouldn't both be "OFF" with equal visual weight.
- Add **review state** per finding: `unreviewed → acknowledged → accepted-variance → rejected (must fix)`. Persist locally (browser storage analogue for Streamlit = session state + a small JSON sidecar in the workspace folder).
- Add a **"what changed since last load"** badge — diff against the prior model upload so the reviewer focuses on net-new exceptions.

---

## 6. Charts & analytical visuals

**Current state.** Four chart builders exist (`build_capex_waterfall`, `build_value_driver_chart`, `build_delta_chart`, `build_sensitivity_tornado`). Solid foundation. But:

- The sensitivity tornado uses **rough heuristic multipliers** (hard-coded ±10% × estimated coefficient). For an investor-grade tool this is a credibility risk — the reviewer will ask "where did these come from?" and there's no good answer. Sensitivities need to be either model-driven (re-run via xlwings against a perturbed copy of the model) or labeled as "directional estimates" with the methodology disclosed in-chart.
- No **capital stack / sources & uses** visual. For an MIPA review, this is table stakes — equity / tax equity / debt / sponsor stack on a single bar with the bible-expected stack alongside.
- No **time-series cash flow** visual. A 25-year project cash flow profile (operating CF + tax benefits + terminal value) tells the reviewer in one image what 200 rows of model output can't.
- No **comparable-project overlay**. The mapper output enables this — show the developer's stated assumptions vs the model's vs the bible on the same axis.

**Recommendation chart additions.**

- **Bible variance bar.** Per project, horizontal bars showing each bible-tracked field's deviation from canonical, sorted by $-impact, color-coded by status. This *is* the IC narrative on one panel.
- **Capital stack waterfall** with bible/model/dev side-by-side.
- **25-year cash flow stacked area** with sensitivity envelope.
- **Portfolio heatmap** (already noted under §4).
- **Sensitivity tornado, but model-driven** — run the existing 38DN convergence solver against a perturbed input set and plot the actual ΔNPP, not a heuristic. Until that's wired up, label the chart "Directional sensitivity (heuristic — verify against model run)".

---

## 7. Workflow / friction

**Current state.** Every analysis requires re-uploading three files, re-selecting projects, re-applying filters. There's no notion of a *review session* that persists.

**Recommendation.**

- Save uploaded files to the workspace folder; on next launch, default to the most recent set with a "use last session" prompt.
- Sticky project selection across mode switches.
- One-click **"IC pack"** export: pulls the current findings, comparison tables, charts, and review decisions into a single PDF deck ready for committee.

---

## 8. Export & handoff

**Current state.** Existing xlsx/pptx/pdf exports do not carry the audit highlighting. The exported artifact is a different (less informative) document than the on-screen view.

**Recommendation.**

- Propagate audit status into all exports (cell fills in xlsx, colored shapes in pptx, colored backgrounds in pdf).
- Export should include the **Findings Ledger** as the first page, not the last. The on-screen narrative order should match the export order.

---

## 9. Aesthetic / brand polish

**Current state.** 38DN palette is applied consistently and the Century Gothic typography reads as on-brand. But the hero banner, KPI cards, and tab strip feel like three different visual systems coexisting. Card borders are inconsistent (some 1px subtle, some 2.5px accent left-bar), and the spacing rhythm jumps between 0.6rem and 1.2rem with no clear logic.

**Recommendation.**

- Settle on a **single 4px spacing grid** (4/8/12/16/24/32) and apply ruthlessly.
- One card style, one elevation, one border treatment — variation only via the left-bar accent color. Linear/Stripe/Ramp aesthetic: lots of whitespace at the macro level, dense within cards.
- Replace the hero gradient banner with a thinner, flatter top bar — the gradient fights the data density underneath it.
- Treat the audit chip strip as a *primary navigational element*, not a legend tucked above a table.

---

## Priority ranking

If I could ship one change: **portfolio audit summary strip + first-class findings ledger with $-impact**. That single change moves the tool from "model inspector" to "IC decision support."

If I could ship three: add the **bible variance bar chart** per project, and **propagate audit highlighting into the pptx/pdf exports** so the on-screen view and the IC pack tell the same story.
