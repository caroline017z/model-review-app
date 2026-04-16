"""
38DN Pricing Model Review
Validates Project Inputs against the Pricing Bible Q1 2026 and Developer Data Room.
Supports Model 1 vs Model 2 comparison with delta analysis.
"""

import logging
import os
import sys
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

# Configure logging once at app entry. Level is env-tunable; default INFO so
# _build_row_mapping / _safe_audit warnings surface in Streamlit Cloud's
# stderr without needing extra config.
logging.basicConfig(
    level=os.environ.get("VP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from mockup_view import (
    render_html as render_mockup_html,
    list_candidate_projects,
    filter_projects,
)
from config import BIBLE_BENCHMARKS
from styles import APP_CSS, SIDEBAR_CHECKBOX_CSS, run_button_css
from data_loader import load_pricing_model, get_projects, load_mapper_output
from benchmark_store import load_overrides, save_overrides, delete_overrides, apply_overrides

# --- Optional Macro Runner integration ---
# Set VP_MACRO_RUNNER_DIR to enable; leave unset to keep the UI hidden.
# Deployed Streamlit Cloud and other multi-user environments should NOT
# ship with a default path, which would leak a local username.
_MACRO_RUNNER_DIR = os.environ.get("VP_MACRO_RUNNER_DIR", "").strip()
_MACRO_RUNNER_DB = os.environ.get("VP_MACRO_RUNNER_DB", "").strip()
_MACRO_RUNNER_AVAILABLE = False
if _MACRO_RUNNER_DIR and Path(_MACRO_RUNNER_DIR).is_dir():
    if _MACRO_RUNNER_DIR not in sys.path:
        sys.path.append(_MACRO_RUNNER_DIR)
    try:
        from vp_bridge import (
            list_available_runs as _mr_list_runs,
            list_available_batches as _mr_list_batches,
            load_run_as_model as _mr_load_run,
            load_batch_as_model as _mr_load_batch,
        )
        _MACRO_RUNNER_AVAILABLE = True
    except ImportError:
        _MACRO_RUNNER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="38DN Pricing Model Review",
    layout="wide",
    page_icon="\u2600",
    initial_sidebar_state="expanded",
)

st.markdown(APP_CSS, unsafe_allow_html=True)

# Make Streamlit's native sidebar collapse/expand handle prominent and keep
# it visible even when the sidebar is collapsed. Ships as an always-on
# teal pill on the top-left so the reviewer can toggle the panel without
# hunting for a faint chevron.
st.markdown(
    """
    <style>
      /* Collapsed-state handle — the floating chevron Streamlit shows when
         the sidebar is hidden. Make it a teal pill that pops off the page. */
      [data-testid="collapsedControl"],
      [data-testid="stSidebarCollapsedControl"] {
        position: fixed !important;
        top: 8px !important;
        left: 8px !important;
        z-index: 9999 !important;
        background: #518484 !important;   /* 38DN teal */
        color: #fff !important;
        border: 1px solid #3d6868 !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        box-shadow: 0 2px 6px rgba(5,13,37,0.18) !important;
        opacity: 1 !important;
        visibility: visible !important;
      }
      [data-testid="collapsedControl"]:hover,
      [data-testid="stSidebarCollapsedControl"]:hover {
        background: #3d6868 !important;
      }
      [data-testid="collapsedControl"] svg,
      [data-testid="stSidebarCollapsedControl"] svg {
        color: #fff !important;
        fill: #fff !important;
        width: 18px !important;
        height: 18px !important;
      }

      /* Expanded-state collapse button (lives inside the sidebar header). */
      [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
      [data-testid="stSidebar"] button[kind="header"] {
        background: #518484 !important;
        color: #fff !important;
        border: 1px solid #3d6868 !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
      }
      [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg,
      [data-testid="stSidebar"] button[kind="header"] svg {
        color: #fff !important;
        fill: #fff !important;
      }

      /* Sidebar selection-control buttons: All / None bulk toggles AND the
         Confirm-selection primary button — all teal, matching the 38DN
         palette. Targets all sidebar buttons. */
      [data-testid="stSidebar"] .stButton > button {
        background: #518484 !important;
        color: #fff !important;
        border: 1px solid #3d6868 !important;
        font-weight: 600 !important;
      }
      [data-testid="stSidebar"] .stButton > button:hover {
        background: #3d6868 !important;
        color: #fff !important;
        border-color: #3d6868 !important;
      }
      /* Streamlit primary button override: same teal even when type=primary. */
      [data-testid="stSidebar"] .stButton > button[kind="primary"],
      [data-testid="stSidebar"] .stButton > button[kind="primaryFormSubmit"] {
        background: #518484 !important;
        color: #fff !important;
        border: 1px solid #3d6868 !important;
      }
      [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: #3d6868 !important;
      }
      /* Disabled state — keep visually distinct but still on-brand. */
      [data-testid="stSidebar"] .stButton > button:disabled {
        background: #d8e0e0 !important;
        color: #7d8694 !important;
        border-color: #c4cccc !important;
        opacity: 0.7 !important;
      }

      /* Partial collapse: keep a slim strip on the left even when the
         sidebar reports as hidden, so the teal handle always has a home.
         Streamlit hides the sidebar via aria-expanded="false"; we nudge
         the main column to leave ~48px of headroom on the left. */
      section[data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 0 !important;
        width: 0 !important;
      }
      section[data-testid="stSidebar"][aria-expanded="false"] ~ section .block-container,
      section[data-testid="stSidebar"][aria-expanded="false"] + section .block-container {
        padding-left: 44px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Let the embedded mockup extend to the viewport edges.
st.markdown(
    """
    <style>
      /* Zero the default gutters on every layer Streamlit puts between the
         sidebar edge and the component iframe, but keep a small left gap so
         the iframe doesn't butt up flush against the sidebar border. */
      [data-testid="stAppViewContainer"] > section.main,
      [data-testid="stMain"],
      [data-testid="stMain"] > div,
      section.main > div,
      .main .block-container,
      .block-container {
        padding-right: 0 !important;
        padding-top: 0 !important;
        max-width: 100% !important;
      }
      /* Small breathing-room strip between the sidebar edge and the mockup. */
      .main .block-container {
        padding-top: 0.25rem !important;
        padding-left: 10px !important;
      }
      /* When the sidebar is collapsed, keep the 44px reserved for the
         always-visible teal chevron (set below) — no extra gap needed. */
      section[data-testid="stSidebar"][aria-expanded="false"] ~ section .block-container,
      section[data-testid="stSidebar"][aria-expanded="false"] + section .block-container {
        padding-left: 44px !important;
      }

      /* Make every vertical block and element container full width. */
      [data-testid="stVerticalBlock"],
      [data-testid="stVerticalBlockBorderWrapper"],
      [data-testid="stElementContainer"],
      .element-container {
        width: 100% !important;
        max-width: 100% !important;
      }

      /* Component iframe: fill parent. Streamlit sometimes bakes a pixel
         width as an HTML attribute — these rules force it back to 100%. */
      iframe,
      iframe[title="streamlit_component"],
      iframe[title^="st."],
      [data-testid="stIFrame"] iframe,
      [data-testid="element-container"] iframe {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
      }

      /* Hide the empty header strip and its shadow. */
      header[data-testid="stHeader"] { background: transparent; height: 0; }
    </style>
    <script>
      // Streamlit measures component width at mount time and can leave the
      // iframe at a frozen px value when the sidebar collapses/expands. Nudge
      // the width back to 100% on every ResizeObserver hit.
      (function () {
        const forceFull = () => {
          document.querySelectorAll('iframe').forEach(el => {
            if (el.getAttribute('width')) el.removeAttribute('width');
            el.style.width = '100%';
          });
        };
        forceFull();
        const ro = new ResizeObserver(forceFull);
        ro.observe(document.documentElement);
        window.addEventListener('resize', forceFull);
        // Also watch the sidebar toggling.
        const sb = document.querySelector('[data-testid="stSidebar"]');
        if (sb) new MutationObserver(forceFull).observe(sb, {attributes:true});
      })();
    </script>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def guess_label(uploaded_file, fallback):
    """Extract label from filename: strip '38DN-' prefix, '_Pricing Model_', and extension."""
    if uploaded_file is None:
        return fallback
    name = Path(uploaded_file.name).stem
    for prefix in ["38DN-", "38DN_", "38DN "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    for mid in ["_Pricing Model_", "_Pricing Model", " Pricing Model ", "_Pricing_Model_",
                 "Pricing Model_", "Pricing Model ", "Pricing_Model_", "Pricing_Model "]:
        name = name.replace(mid, " ")
    return name.strip() if name.strip() else fallback


def render_sidebar():
    with st.sidebar:
        st.markdown("### Model 1 (Primary)")
        model_file = st.file_uploader("Upload Pricing Model", type=["xlsm", "xlsx"], key="m1")
        m1_fname = model_file.name if model_file else None
        if m1_fname != st.session_state.get("_m1_prev_file"):
            st.session_state["_m1_prev_file"] = m1_fname
            st.session_state["m1l"] = guess_label(model_file, "Model 1")
        m1_label = st.text_input("Model 1 Label", key="m1l")

        st.markdown("---")
        st.markdown("### Model 2 (Comparison)")
        model_file_2 = st.file_uploader("Upload second model (optional)", type=["xlsm", "xlsx"], key="m2",
                                        help="A different market, previous iteration, or scenario")
        m2_fname = model_file_2.name if model_file_2 else None
        if m2_fname != st.session_state.get("_m2_prev_file"):
            st.session_state["_m2_prev_file"] = m2_fname
            st.session_state["m2l"] = guess_label(model_file_2, "Model 2")
        m2_label = st.text_input("Model 2 Label", key="m2l")

        st.markdown("---")
        st.markdown("### Mapper Output (optional)")
        mapper_file = st.file_uploader(
            "Portfolio-Model-Mapper output",
            type=["xlsx"], key="mapper",
            help="Output from /portfolio-model-mapper. Adds a third comparison column (Developer Inputs) and feeds the bible audit.",
        )

        st.markdown("---")
        st.markdown("### Data Room")
        dr_files = st.file_uploader("Developer files (optional)", type=["xlsx"], accept_multiple_files=True)

        # --- Macro Runner integration ---
        if _MACRO_RUNNER_AVAILABLE:
            st.markdown("---")
            with st.expander("Load from Macro Runner"):
                _mr_db_path = st.text_input(
                    "SQLite DB Path",
                    value=_MACRO_RUNNER_DB,
                    key="mr_db_path",
                )
                _mr_db_exists = Path(_mr_db_path).exists()
                if not _mr_db_exists:
                    st.warning("Database file not found at this path.")
                else:
                    _mr_mode = st.radio(
                        "Load mode", ["Single Run", "Batch"],
                        horizontal=True, key="mr_mode",
                    )
                    if _mr_mode == "Single Run":
                        _mr_runs = _mr_list_runs(_mr_db_path)
                        if not _mr_runs:
                            st.info("No successful runs found in this database.")
                        else:
                            _mr_labels = [r["display_label"] for r in _mr_runs]
                            _mr_sel = st.selectbox("Select run", _mr_labels, key="mr_run_sel")
                            _mr_sel_idx = _mr_labels.index(_mr_sel) if _mr_sel else 0
                            _mr_selected_run = _mr_runs[_mr_sel_idx]
                            if st.button("Load Run", key="mr_load_btn"):
                                _mr_result = _mr_load_run(_mr_db_path, _mr_selected_run["id"])
                                st.session_state["mr_loaded_model"] = _mr_result
                                st.session_state["mr_loaded_label"] = (
                                    f"Macro: {_mr_selected_run['project_name'] or _mr_selected_run['workbook_name']}"
                                )
                                st.success(
                                    f"Loaded {len(_mr_result.get('projects', {}))} project(s) from macro run."
                                )
                    else:  # Batch mode
                        _mr_batches = _mr_list_batches(_mr_db_path)
                        if not _mr_batches:
                            st.info("No batches found in this database.")
                        else:
                            _mr_blabels = [b["display_label"] for b in _mr_batches]
                            _mr_bsel = st.selectbox("Select batch", _mr_blabels, key="mr_batch_sel")
                            _mr_bsel_idx = _mr_blabels.index(_mr_bsel) if _mr_bsel else 0
                            _mr_selected_batch = _mr_batches[_mr_bsel_idx]
                            if st.button("Load Batch", key="mr_load_batch_btn"):
                                _mr_result = _mr_load_batch(
                                    _mr_db_path, _mr_selected_batch["batch_id"]
                                )
                                st.session_state["mr_loaded_model"] = _mr_result
                                st.session_state["mr_loaded_label"] = (
                                    f"Macro: {_mr_selected_batch['workbook_name']} "
                                    f"({_mr_selected_batch['project_count']} projects)"
                                )
                                st.success(
                                    f"Loaded {len(_mr_result.get('projects', {}))} project(s) from batch."
                                )

                    # Option to use loaded macro data as Model 1 or Model 2
                    if st.session_state.get("mr_loaded_model"):
                        _mr_target = st.radio(
                            "Use as", ["Model 1", "Model 2"],
                            horizontal=True, key="mr_target",
                        )
                        st.caption(
                            f"Currently loaded: {st.session_state.get('mr_loaded_label', '—')}"
                        )

        st.markdown("---")
        st.markdown(SIDEBAR_CHECKBOX_CSS, unsafe_allow_html=True)
        # --- Persistent benchmark tuning ---
        # Operate on a session-scoped copy of BIBLE_BENCHMARKS so one reviewer's
        # overrides don't bleed into another reviewer's session on the shared
        # Streamlit Cloud process.
        if "bible_benchmarks" not in st.session_state:
            import copy as _copy
            st.session_state["bible_benchmarks"] = _copy.deepcopy(BIBLE_BENCHMARKS)
        overrides = load_overrides()
        apply_overrides(st.session_state["bible_benchmarks"], overrides)

        bench_on = st.checkbox("Benchmark Tuning", value=False, key="bench_toggle")
        if bench_on:
            # Show count of custom-tuned benchmarks
            if overrides:
                st.caption(f"{len(overrides)} benchmark(s) custom-tuned")

            all_checks = {}
            for cat, checks in st.session_state["bible_benchmarks"].items():
                for label, spec in checks.items():
                    if not spec.get("derived"):
                        all_checks[f"{cat} | {label}"] = (cat, label)
            sel_bench = st.selectbox("Select parameter", options=sorted(all_checks.keys()), key="bench_sel")
            if sel_bench and sel_bench in all_checks:
                cat_key, label_key = all_checks[sel_bench]
                spec = st.session_state["bible_benchmarks"][cat_key][label_key]
                override_key = f"{cat_key}|{label_key}"
                bc1, bc2 = st.columns(2)
                with bc1:
                    new_min = st.number_input("Lower bound", value=float(spec["min"]), step=0.01, format="%.3f", key="bench_min")
                with bc2:
                    new_max = st.number_input("Upper bound", value=float(spec["max"]), step=0.01, format="%.3f", key="bench_max")
                st.session_state["bible_benchmarks"][cat_key][label_key]["min"] = new_min
                st.session_state["bible_benchmarks"][cat_key][label_key]["max"] = new_max
                # Persist change if different from current stored value
                cur = overrides.get(override_key, {})
                if cur.get("min") != new_min or cur.get("max") != new_max:
                    overrides[override_key] = {"min": new_min, "max": new_max}
                    save_overrides(overrides)
                st.caption(f"Unit: {spec['unit']}  |  Row: {spec['row']}")

            # Reset button
            if overrides:
                if st.button("Reset to Defaults", key="bench_reset"):
                    delete_overrides()
                    st.rerun()

        # Run button
        st.markdown("---")
        has_model = (model_file is not None or model_file_2 is not None
                     or st.session_state.get("mr_loaded_model") is not None)
        already_run = st.session_state.get("review_active", False) and has_model

        if has_model and already_run:
            css = run_button_css("rgba(81,132,132,0.15)", "#518484", "rgba(81,132,132,0.25)", "#518484", "white")
            btn_label = "\u2713  REVIEW ACTIVE"
        elif has_model:
            css = run_button_css("#518484", "white", "rgba(81,132,132,0.5)", "#3d6868", "white")
            btn_label = "\u25B6  RUN REVIEW"
        else:
            css = run_button_css("#eef0f5", "#9ca3af", "rgba(5,13,37,0.06)", "#eef0f5", "#9ca3af")
            btn_label = "\u25B6  RUN REVIEW"

        st.markdown(css, unsafe_allow_html=True)
        run_clicked = st.button(btn_label, key="run_btn", use_container_width=True, disabled=not has_model)

        if run_clicked:
            st.session_state["review_active"] = True
        review_active = st.session_state.get("review_active", False) and has_model

        if not has_model:
            st.session_state["review_active"] = False
            review_active = False

        if has_model and not review_active:
            st.caption("Upload detected \u2014 press RUN REVIEW to analyze")

    return model_file, model_file_2, m1_label, m2_label, dr_files, review_active, mapper_file


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.markdown("""
    <div class="hero-banner">
        <h1>38DN Pricing Model Review</h1>
        <p>Model validation, comparison &amp; market assumptions \u2014 Q1 2026 Pricing Bible</p>
    </div>
    """, unsafe_allow_html=True)

    model_file, model_file_2, m1_label, m2_label, dr_files, review_active, mapper_file = render_sidebar()

    # --- Check for macro runner loaded data ---
    mr_model = st.session_state.get("mr_loaded_model")
    mr_target = st.session_state.get("mr_target", "Model 1")
    mr_label = st.session_state.get("mr_loaded_label", "Macro Runner")

    # If macro runner data is loaded, treat it as having a model present
    has_mr_m1 = mr_model is not None and mr_target == "Model 1"
    has_mr_m2 = mr_model is not None and mr_target == "Model 2"

    has_any_model = model_file is not None or model_file_2 is not None or mr_model is not None
    if has_mr_m1 and not model_file:
        # Auto-activate review when macro runner data is loaded as Model 1
        review_active = st.session_state.get("review_active", False) or True
    if has_mr_m2 and not model_file_2:
        review_active = st.session_state.get("review_active", False) or True

    # Load data once — only what the review mockup actually consumes.
    merged_projects: dict = {}
    candidates: list[dict] = []
    if review_active and has_any_model:
        with st.status("Loading review data…", expanded=True) as _status:
            # Model 1: prefer uploaded file, fall back to macro runner
            if model_file:
                _status.update(label=f"Parsing pricing model: {getattr(model_file, 'name', m1_label)}…")
                m1_result = load_pricing_model(model_file)
            elif has_mr_m1:
                _status.update(label=f"Loading pricing model from macro runner: {mr_label}…")
                m1_result = mr_model
                m1_label = mr_label
            else:
                m1_result = None

            _status.update(label="Extracting projects…")
            m1_projects = get_projects(m1_result) if m1_result else {}

            if mapper_file:
                _status.update(label="Loading mapper output…")
                mapper_projects = load_mapper_output(mapper_file) or {}
            else:
                mapper_projects = {}

            merged_projects = dict(m1_projects)
            for k, v in mapper_projects.items():
                if isinstance(k, str) and k.startswith("_"):
                    continue
                merged_projects.setdefault(k, v)

            _status.update(label="Identifying active projects…")
            candidates = list_candidate_projects(merged_projects)
            n_active = sum(1 for c in candidates if c["toggled_on"])
            n_sibling = sum(1 for c in candidates if c.get("dev_sibling"))
            n_other = len(candidates) - n_active - n_sibling
            parts = [f"{n_active} toggled=On"]
            if n_sibling:
                parts.append(f"+ {n_sibling} same-developer")
            if n_other:
                parts.append(f"({n_other} other available)")
            _status.update(
                label="Review ready — " + " ".join(parts),
                state="complete",
                expanded=False,
            )

    # Sidebar: let reviewer pick which project columns to review, with a
    # two-phase commit — checkbox changes are 'pending' until the reviewer
    # clicks Confirm. The mockup only re-renders against `confirmed_ids`, so
    # mid-edit ticks don't thrash the Project Review panel.
    pending_ids: set[str] = set()
    if candidates:
        # Suggested = row-7 toggle=On OR same developer as an On project.
        # Both default-checked; off-siblings get a small visual cue so the
        # reviewer knows they were pulled in via the developer-match rule.
        suggested = [c for c in candidates if c.get("suggested")]
        others    = [c for c in candidates if not c.get("suggested")]

        def _grouped(items):
            buckets: dict[str, list[dict]] = {}
            for c in items:
                buckets.setdefault(c["developer"] or "— unspecified —", []).append(c)
            return sorted(buckets.items(), key=lambda kv: kv[0].lower())

        def _item_label(c):
            # Disambiguates duplicate-named projects via the model's own
            # Project # (row 2 of Project Inputs). The Excel column letter
            # is intentionally NOT shown — Project # is the canonical
            # identifier reviewers track in the Returns sheets.
            head_parts = []
            if c.get("proj_number") is not None:
                head_parts.append(f"`P{c['proj_number']}`")
            head_parts.append(f"**{c['name']}**")
            head = " ".join(head_parts)
            meta = " · ".join([x for x in [c["state"], c["utility"], c["program"]] if x])
            dc_str = f"{c['dc']:.2f} MW" if c["dc"] else ""
            cue = ""
            if not c["toggled_on"] and c.get("dev_sibling"):
                cue = "  ·  *same-dev (toggle=Off)*"
            elif not c["toggled_on"]:
                cue = "  ·  *toggle=Off*"
            tail = " — ".join([x for x in [meta, dc_str] if x])
            return head + cue + (f"  \n{tail}" if tail else "")

        def _render_group(items, default_checked):
            for dev, grp in _grouped(items):
                st.markdown(f"**{dev}**")
                for c in grp:
                    sig = f"inc::{model_key}::{c['id']}::{c['name']}"
                    checked = st.checkbox(_item_label(c), value=default_checked, key=sig)
                    if checked:
                        pending_ids.add(str(c["id"]))

        with st.sidebar:
            st.markdown("---")
            st.markdown("### Projects in review")
            n_on = sum(1 for c in suggested if c["toggled_on"])
            n_sib = sum(1 for c in suggested if c.get("dev_sibling"))
            sug_mw = sum(c["dc"] for c in suggested)
            pieces = [f"{n_on} toggled=On"]
            if n_sib:
                pieces.append(f"+ {n_sib} same-developer")
            st.caption(
                f"{' '.join(pieces)} · {sug_mw:.1f} MWdc  \n"
                f"({len(others)} other available)"
            )
            model_key = getattr(model_file, "name", None) or m1_label or "model"

            # All / None bulk toggles. Writing to session_state flips every
            # "inc::..." key on the next rerun; individual checkboxes then
            # read the new default.
            def _bulk_toggle(items, value):
                for c in items:
                    st.session_state[f"inc::{model_key}::{c['id']}::{c['name']}"] = value

            if suggested:
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.button("✓ All", key="sug_all", use_container_width=True,
                              on_click=_bulk_toggle, args=(suggested, True))
                with bc2:
                    st.button("✗ None", key="sug_none", use_container_width=True,
                              on_click=_bulk_toggle, args=(suggested, False))
                # Scroll cap so a 30+ project list doesn't eat the sidebar.
                with st.container(height=min(420, 80 + 44 * len(suggested)), border=False):
                    _render_group(suggested, default_checked=True)
            else:
                st.warning(
                    "No projects with row-7 toggle = On. "
                    "Check your pricing model or opt-in via the expander below."
                )

            if others:
                with st.expander(
                    f"+ Other projects ({len(others)})", expanded=False
                ):
                    _render_group(others, default_checked=False)

            # Two-phase commit: initialize confirmed set from the pending set
            # on first load so the default-suggested projects populate the
            # review without requiring an extra click.
            confirm_key = f"confirmed_ids::{model_key}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = set(pending_ids)
            confirmed_ids: set[str] = set(st.session_state[confirm_key])

            dirty = pending_ids != confirmed_ids
            added = pending_ids - confirmed_ids
            removed = confirmed_ids - pending_ids

            pend_mw = sum(c["dc"] for c in candidates if str(c["id"]) in pending_ids)
            st.markdown("---")
            st.caption(
                f"**Pending:** {len(pending_ids)} selected · {pend_mw:.1f} MWdc"
                + (f"  \n*{len(added)} to add · {len(removed)} to remove*" if dirty else "")
            )
            btn_label = "✓ Confirm selection"
            if dirty:
                btn_label = f"✓ Confirm ({len(added)}+/{len(removed)}−)"
            clicked = st.button(
                btn_label,
                key=f"confirm_btn::{model_key}",
                type="primary",
                use_container_width=True,
                disabled=not dirty,
                help="Apply pending checkbox changes to the Project Review panel.",
            )
            if clicked:
                st.session_state[confirm_key] = set(pending_ids)
                confirmed_ids = set(pending_ids)
                dirty = False
                # Toast confirms the click registered, in case the visual
                # change (counts above) isn't obvious.
                try:
                    st.toast(
                        f"Updated review: {len(confirmed_ids)} project(s) "
                        f"({len(added)} added, {len(removed)} removed)",
                        icon="✅",
                    )
                except Exception:
                    pass

            conf_mw = sum(c["dc"] for c in candidates if str(c["id"]) in confirmed_ids)
            tag = "↻ Unsaved changes" if dirty else "✓ In sync with review"
            st.caption(
                f"**In review:** {len(confirmed_ids)} project(s) · {conf_mw:.1f} MWdc  \n"
                f"<span style=\"color:{'var(--out,#518484)' if dirty else 'var(--ok,#3a7d44)'};font-weight:600;\">{tag}</span>",
                unsafe_allow_html=True,
            )

    review_projects = filter_projects(merged_projects, confirmed_ids) if candidates else {}

    # Visible status strip just above the iframe so the reviewer can sanity-
    # check what the embedded mockup is being asked to render. If this number
    # disagrees with what the iframe shows, it's a render bug — not a filter
    # bug — so direct people to a hard reload.
    n_review = len(review_projects)
    if n_review:
        st.markdown(
            f"<div style=\"font-size:11px;color:#7d8694;padding:4px 12px;"
            f"background:#eef0f5;border-bottom:1px solid rgba(5,13,37,0.08);\">"
            f"<b>{n_review}</b> project(s) sent to the review panel."
            f"</div>",
            unsafe_allow_html=True,
        )
    elif candidates:
        st.warning(
            "No projects in the current confirmed selection. Tick at least one "
            "in the sidebar and click **Confirm selection** to populate the "
            "Project Review panel."
        )

    mockup_html = render_mockup_html(
        review_projects,
        model_label=m1_label or "Model 1",
        reviewer="Caroline Z.",
        bible_label="Q1 '26",
    )
    # Cache-bust the iframe by suffixing a deterministic hash of the payload
    # as an HTML comment. Streamlit's component diffing reuses the iframe when
    # the HTML is byte-identical; injecting the hash guarantees a fresh frame
    # whenever the project set changes.
    import hashlib as _hashlib
    payload_sig = _hashlib.md5(
        ("|".join(sorted(str(c) for c in review_projects.keys())) or "empty").encode("utf-8")
    ).hexdigest()[:10]
    mockup_html = mockup_html.replace(
        "</body>",
        f"<!-- vp-review payload sig: {payload_sig} -->\n</body>",
    )
    components.html(mockup_html, height=1400, scrolling=True)


if __name__ == "__main__":
    main()
