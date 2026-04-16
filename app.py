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

# Let the embedded mockup extend to the viewport edges.
st.markdown(
    """
    <style>
      /* Zero the default gutters on every layer Streamlit puts between the
         sidebar edge and the component iframe. */
      [data-testid="stAppViewContainer"] > section.main,
      [data-testid="stMain"],
      [data-testid="stMain"] > div,
      section.main > div,
      .main .block-container,
      .block-container {
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-top: 0 !important;
        max-width: 100% !important;
      }
      /* The block-container normally has top padding for the hidden header;
         we want a thin gap instead of zero so the top bar isn't glued. */
      .main .block-container { padding-top: 0.25rem !important; }

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

            _status.update(
                label=f"Review ready — suggesting {len(candidates)} active project(s)",
                state="complete",
                expanded=False,
            )

    # Sidebar: let reviewer pick which project columns to review. Active
    # (row 7 = On) ones default checked; inactive ones are listed below and
    # default unchecked so the reviewer can opt them in.
    included_ids: set[str] = set()
    if candidates:
        # Default-on = toggle=On OR (toggle=Off AND shares developer with an On project).
        # Everything else is opt-in via the expander.
        suggested = [c for c in candidates if c.get("suggested")]
        extras = [c for c in candidates if not c.get("suggested")]

        def _grouped(items):
            buckets: dict[str, list[dict]] = {}
            for c in items:
                buckets.setdefault(c["developer"] or "— unspecified —", []).append(c)
            return sorted(buckets.items(), key=lambda kv: kv[0].lower())

        def _item_label(c):
            meta = " · ".join([x for x in [c["state"], c["utility"], c["program"]] if x])
            dc_str = f"{c['dc']:.2f} MW" if c["dc"] else ""
            off_tag = "" if c["toggled_on"] else "  ·  *toggle=Off*"
            tail = " — ".join([x for x in [meta, dc_str] if x])
            return f"**{c['name']}**" + off_tag + (f"  \n{tail}" if tail else "")

        with st.sidebar:
            st.markdown("---")
            st.markdown("### Projects in review")
            sug_mw = sum(c["dc"] for c in suggested)
            n_on = sum(1 for c in suggested if c["toggled_on"])
            n_dev = len(suggested) - n_on
            st.caption(
                f"{len(suggested)} suggested · {sug_mw:.1f} MWdc  \n"
                f"({n_on} toggled=On"
                + (f" + {n_dev} same-developer" if n_dev else "")
                + f" · {len(extras)} other available)"
            )
            model_key = getattr(model_file, "name", None) or m1_label or "model"

            for dev, items in _grouped(suggested):
                st.markdown(f"**{dev}**")
                for c in items:
                    sig = f"inc::{model_key}::{c['id']}::{c['name']}"
                    checked = st.checkbox(_item_label(c), value=True, key=sig)
                    if checked:
                        included_ids.add(str(c["id"]))

            if extras:
                with st.expander(f"+ Add other projects ({len(extras)})", expanded=False):
                    for dev, items in _grouped(extras):
                        st.markdown(f"**{dev}**")
                        for c in items:
                            sig = f"inc::{model_key}::{c['id']}::{c['name']}"
                            checked = st.checkbox(_item_label(c), value=False, key=sig)
                            if checked:
                                included_ids.add(str(c["id"]))

            n_included = len(included_ids)
            n_total_mw = sum(c["dc"] for c in candidates if str(c["id"]) in included_ids)
            st.caption(f"→ Reviewing **{n_included}** project(s) · **{n_total_mw:.1f} MWdc**")

    review_projects = filter_projects(merged_projects, included_ids) if candidates else {}

    mockup_html = render_mockup_html(
        review_projects,
        model_label=m1_label or "Model 1",
        reviewer="Caroline Z.",
        bible_label="Q1 '26",
    )
    components.html(mockup_html, height=1400, scrolling=True)


if __name__ == "__main__":
    main()
