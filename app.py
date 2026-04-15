"""
38DN Pricing Model Review
Validates Project Inputs against the Pricing Bible Q1 2026 and Developer Data Room.
Supports Model 1 vs Model 2 comparison with delta analysis.
"""

import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

from config import (
    P, CHART_COLORS, BIBLE_BENCHMARKS, MARKET_CONFIGS, MARKET_HIERARCHY,
    CS_CAPEX, CS_OPEX, CS_CONSTRUCTION_LOAN, CS_PERM_DEBT_FRONT, CS_DSCR_FRONT,
    CS_PERM_DEBT_BACK, CS_DSCR_BACK, CS_TAX_EQUITY, CS_EPC_SPEND, STATE_NOTES,
    INPUT_ROW_LABELS, OUTPUT_ROWS, PCT_ROWS, TEXT_ROWS, DATE_ROWS, PLOTLY_BG,
    DISPLAY_ORDER, SECTION_BREAKS,
)
from styles import APP_CSS, SIDEBAR_CHECKBOX_CSS, run_button_css
from utils import (
    safe_float, fmt_dollar_w, fmt_row_val, kpi_card, styled_plotly,
    fmt_val, fmt_delta, style_field_header, style_delta, style_flag, style_warn, style_status,
)
from data_loader import (load_pricing_model, get_projects, get_ops_sandbox,
                         get_rate_curves, load_data_room, load_gh25_reference,
                         load_mapper_output)
from validation import validate_project
from bible_audit import audit_project, status_class, status_tooltip
from benchmark_store import load_overrides, save_overrides, delete_overrides, apply_overrides
from charts import build_capex_waterfall, build_value_driver_chart, build_delta_chart, build_sensitivity_tornado
from comparison import (
    build_comparison_table, compute_portfolio_wtd_avg,
    render_bible_section, render_market_card,
)
from xlsx_export import (generate_comparison_xlsx, generate_multi_project_xlsx,
                         build_export_rows, generate_review_xlsx)
from pptx_export import generate_pptx
from pdf_export import generate_pdf

# --- Macro Runner integration ---
_MACRO_RUNNER_DIR = r"C:\Users\CarolineZepecki\projects\excel_macro_runner"
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
                    value=r"C:\Users\CarolineZepecki\projects\excel_macro_runner\results.db",
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
        overrides = load_overrides()
        apply_overrides(BIBLE_BENCHMARKS, overrides)

        bench_on = st.checkbox("Benchmark Tuning", value=False, key="bench_toggle")
        if bench_on:
            # Show count of custom-tuned benchmarks
            if overrides:
                st.caption(f"{len(overrides)} benchmark(s) custom-tuned")

            all_checks = {}
            for cat, checks in BIBLE_BENCHMARKS.items():
                for label, spec in checks.items():
                    if not spec.get("derived"):
                        all_checks[f"{cat} | {label}"] = (cat, label)
            sel_bench = st.selectbox("Select parameter", options=sorted(all_checks.keys()), key="bench_sel")
            if sel_bench and sel_bench in all_checks:
                cat_key, label_key = all_checks[sel_bench]
                spec = BIBLE_BENCHMARKS[cat_key][label_key]
                override_key = f"{cat_key}|{label_key}"
                bc1, bc2 = st.columns(2)
                with bc1:
                    new_min = st.number_input("Lower bound", value=float(spec["min"]), step=0.01, format="%.3f", key="bench_min")
                with bc2:
                    new_max = st.number_input("Upper bound", value=float(spec["max"]), step=0.01, format="%.3f", key="bench_max")
                BIBLE_BENCHMARKS[cat_key][label_key]["min"] = new_min
                BIBLE_BENCHMARKS[cat_key][label_key]["max"] = new_max
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
# Tab renderers
# ---------------------------------------------------------------------------

def tab_portfolio(m1_projects, m2_projects, m1_label, m2_label, model_file_2, review_active, model_file):
    if not review_active or not model_file:
        st.markdown('<div style="text-align:center;padding:3rem;"><p style="font-size:0.95rem;font-weight:600;color:#212B48;">Upload a model and press RUN REVIEW</p><p style="font-size:0.78rem;color:#7a8291;">Portfolio View shows MWdc-weighted average inputs across all active projects</p></div>', unsafe_allow_html=True)
        return

    active1 = {k: v for k, v in m1_projects.items() if v["toggle"]}
    p2_active = {k: v for k, v in m2_projects.items() if v["toggle"]} if m2_projects else None

    port1 = compute_portfolio_wtd_avg(active1)
    port2 = compute_portfolio_wtd_avg(p2_active) if p2_active else None

    st.markdown(f"""
    <div class="kpi-row">
        {kpi_card(f"{m1_label} Projects", str(port1["_proj_count"]), f"{port1['_total_mw']:.1f} MWdc total", "accent")}
        {kpi_card(f"{m1_label} Wtd Dev Fee", fmt_dollar_w(port1.get(32)), "$/W (MWdc-wtd)", "teal")}
        {kpi_card(f"{m1_label} Wtd FMV", fmt_dollar_w(port1.get(33)), "$/W (MWdc-wtd)", "teal")}
        {kpi_card(f"{m2_label} Projects" if port2 else "Model 2", str(port2["_proj_count"]) if port2 else "\u2014", f"{port2['_total_mw']:.1f} MWdc total" if port2 else "Not loaded", "accent" if port2 else "warn")}
        {kpi_card(f"{m2_label} Wtd Dev Fee" if port2 else "M2 Dev Fee", fmt_dollar_w(port2.get(32) if port2 else None), "$/W (MWdc-wtd)", "teal")}
    </div>
    """, unsafe_allow_html=True)

    port_match_mode = st.radio("Display", ["Variance Only", "Full Matching"],
                               horizontal=True, key="port_match_mode") if port2 else "Full Matching"
    st.markdown('<div class="section-hdr">Portfolio Weighted Average Comparison (MWdc-Weighted)</div>', unsafe_allow_html=True)

    all_rows = [r for r in DISPLAY_ORDER if r in INPUT_ROW_LABELS or r in OUTPUT_ROWS]
    port_rows = []
    for r in all_rows:
        label = INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}"))
        v1 = port1.get(r)
        v2 = port2.get(r) if port2 else None
        is_pct = r in PCT_ROWS
        is_text = r in TEXT_ROWS or r in DATE_ROWS

        fv = lambda v, _r=r: fmt_row_val(v, _r)

        delta, pct = None, None
        if not is_text and v1 is not None and v2 is not None:
            fv1, fv2 = safe_float(v1), safe_float(v2)
            if fv1 is not None and fv2 is not None:
                delta = fv2 - fv1
                pct = delta / abs(fv1) if fv1 != 0 else None

        row_data = {"Row": r, "Field": label, f"{m1_label} (Wtd Avg)": fv(v1),
                    "_delta_raw": delta}
        if port2:
            row_data[f"{m2_label} (Wtd Avg)"] = fv(v2)
            row_data["Delta (units)"] = fmt_delta(delta, is_pct)
            row_data["Delta (%)"] = fmt_delta(pct, pct_fmt=True)
        port_rows.append(row_data)

    df_port = pd.DataFrame(port_rows)

    if port2 and port_match_mode == "Variance Only":
        df_port = df_port[
            df_port["_delta_raw"].apply(lambda d: d is not None and abs(d) >= 0.000001)
        ].reset_index(drop=True)
    df_port = df_port.drop(columns=["_delta_raw"], errors="ignore")

    styler = df_port.style.map(style_field_header, subset=["Field"])
    if port2 and "Delta (units)" in df_port.columns:
        styler = styler.map(style_delta, subset=["Delta (units)", "Delta (%)"])
    st.dataframe(styler, use_container_width=True, hide_index=True, height=600)

    if port2:
        st.markdown(f'<div class="section-hdr">Key Portfolio Deltas <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {m2_label} vs {m1_label} (MWdc-Wtd Avg)</span></div>', unsafe_allow_html=True)
        key_rows = [38, 33, 11, 14, 118, 119, 120, 122, 123, 129, 157, 158, 160, 216, 225, 226, 230, 296, 302, 597, 602]
        delta_bars = []
        for r in key_rows:
            v1f = safe_float(port1.get(r))
            v2f = safe_float(port2.get(r))
            if v1f is not None and v2f is not None and v2f != v1f:
                delta_bars.append({"Field": INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}")), "Delta": v2f - v1f})
        fig_db = build_delta_chart(delta_bars, f"{m1_label} (Wtd)", f"{m2_label} (Wtd)")
        if fig_db:
            st.plotly_chart(fig_db, use_container_width=True, key="port_delta")


def tab_bible():
    st.markdown('<div class="section-hdr">CS Tab \u2014 Q1 2026 Average Assumptions</div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("#### CapEx"); st.dataframe(render_bible_section("CapEx", CS_CAPEX), use_container_width=True, hide_index=True)
        st.markdown("#### OpEx"); st.dataframe(render_bible_section("OpEx", CS_OPEX), use_container_width=True, hide_index=True)
        st.markdown("#### EPC Spend Schedule")
        st.dataframe(pd.DataFrame([{"Month": k, "% of Total": f"{v:.0%}"} for k, v in CS_EPC_SPEND.items()]), use_container_width=True, hide_index=True, height=200)
    with b2:
        st.markdown("#### Construction Loan"); st.dataframe(render_bible_section("CL", CS_CONSTRUCTION_LOAN), use_container_width=True, hide_index=True)
        st.markdown("#### Perm Debt \u2014 Front Leverage"); st.dataframe(render_bible_section("F", CS_PERM_DEBT_FRONT), use_container_width=True, hide_index=True)
        st.markdown("**DSCR Schedule (net of TE)**"); st.dataframe(pd.DataFrame([{"Period": k, "DSCR": f"{v:.2f}x"} for k, v in CS_DSCR_FRONT.items()]), use_container_width=True, hide_index=True)
        st.markdown("#### Perm Debt \u2014 Back Leverage"); st.dataframe(render_bible_section("B", CS_PERM_DEBT_BACK), use_container_width=True, hide_index=True)
        st.markdown("**DSCR Schedule**"); st.dataframe(pd.DataFrame([{"Period": k, "DSCR": f"{v:.2f}x"} for k, v in CS_DSCR_BACK.items()]), use_container_width=True, hide_index=True)
    st.markdown('<div class="section-hdr">Tax Equity Assumptions</div>', unsafe_allow_html=True)
    st.dataframe(render_bible_section("TE", CS_TAX_EQUITY), use_container_width=True, hide_index=True)
    st.markdown('<div class="section-hdr">State-Specific Notes</div>', unsafe_allow_html=True)
    for state, notes in STATE_NOTES.items():
        with st.expander(f"{state}"):
            for n in notes:
                st.markdown(f'<div class="note-box">{n}</div>', unsafe_allow_html=True)


def tab_market():
    st.markdown('<div class="section-hdr">Market Specific Assumptions \u2014 State / Utility / Program Selector</div>', unsafe_allow_html=True)
    mc1, mc2, mc3 = st.columns(3)
    with mc1: sel_state = st.selectbox("State", sorted(MARKET_HIERARCHY.keys()))
    with mc2: sel_util = st.selectbox("Utility", sorted(MARKET_HIERARCHY.get(sel_state, {}).keys()))
    with mc3: sel_prog = st.selectbox("Program", MARKET_HIERARCHY.get(sel_state, {}).get(sel_util, []))
    key = (sel_state, sel_util, sel_prog)
    if key in MARKET_CONFIGS:
        cfg = MARKET_CONFIGS[key]
        st.markdown(f"### {sel_state} \u2014 {sel_util} \u2014 {sel_prog}")
        st.caption(f"Bible column: **{cfg['col']}**")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("#### Incentives & Customer Economics")
            st.markdown(render_market_card(cfg))
        with m2:
            resi = cfg.get("cust_resi", 0)
            if isinstance(resi, (int, float)):
                mix_l, mix_v = [], []
                for seg, k in [("Residential", "cust_resi"), ("Commercial", "cust_comm"), ("Anchor", "cust_anchor"), ("LMI", "cust_lmi")]:
                    v = cfg.get(k, 0)
                    if isinstance(v, (int, float)) and v > 0:
                        mix_l.append(seg); mix_v.append(v)
                if mix_v:
                    fig_pie = go.Figure(go.Pie(labels=mix_l, values=mix_v, marker_colors=[P["blue"], P["green"], P["warn"], P["teal"]], hole=0.45, textinfo="label+percent", textfont=dict(family="DM Sans", size=12)))
                    fig_pie.update_layout(title="Customer Mix", showlegend=False, height=300, margin=dict(t=40, b=20, l=20, r=20), paper_bgcolor=PLOTLY_BG)
                    st.plotly_chart(fig_pie, use_container_width=True, key="mkt_pie")
            disc_data = []
            for seg, k in [("Resi", "disc_resi"), ("Comm", "disc_comm"), ("Anchor", "disc_anchor"), ("LMI", "disc_lmi"), ("Blend", "disc_blend")]:
                v = cfg.get(k)
                if isinstance(v, (int, float)):
                    disc_data.append({"Segment": seg, "Discount": v})
            if disc_data:
                df_disc = pd.DataFrame(disc_data)
                fig_disc = go.Figure(go.Bar(x=df_disc["Segment"], y=df_disc["Discount"], marker_color=[P["blue"], P["green"], P["warn"], P["teal"], P["navy"]][:len(disc_data)], text=[f"{v:.0%}" for v in df_disc["Discount"]], textposition="outside", textfont=dict(family="Century Gothic, DM Sans", size=11)))
                fig_disc.update_layout(title="Customer Discounts", yaxis_title="%", yaxis_tickformat=".0%", showlegend=False)
                st.plotly_chart(styled_plotly(fig_disc, 300), use_container_width=True, key="mkt_disc")
        st.markdown('<div class="section-hdr">Model-Ready Inputs</div>', unsafe_allow_html=True)
        model_inputs = []
        inc_v = cfg.get("upfront_incentive", 0)
        if inc_v:
            model_inputs.append({"Model Row": 216, "Field": "Upfront Incentive", "Value": f"${inc_v:.3f}/W", "Source": "Market Specific"})
            model_inputs.append({"Model Row": 217, "Field": "Incentive Lag", "Value": f"{cfg.get('incentive_lag', 0)} months", "Source": "Market Specific"})
        disc_b = cfg.get("disc_blend")
        if isinstance(disc_b, (int, float)):
            model_inputs.append({"Model Row": 161, "Field": "Rate Discount", "Value": f"{disc_b:.1%}", "Source": "Market Specific"})
        ucb_v = cfg.get("ucb", 0)
        if ucb_v:
            model_inputs.append({"Model Row": 162, "Field": "UCB Fee", "Value": f"{ucb_v:.1%}", "Source": "Market Specific"})
        acq_v = cfg.get("acq_blend")
        if acq_v:
            model_inputs.append({"Model Row": 121, "Field": "Customer Acq (blended)", "Value": f"${acq_v:.4f}/kWh", "Source": "Market Specific"})
        cma_v = cfg.get("cma_blend")
        if cma_v:
            model_inputs.append({"Model Row": 239, "Field": "Customer Mgmt (blended)", "Value": f"${cma_v:.5f}/kWh", "Source": "Market Specific"})
        model_inputs.append({"Model Row": "-", "Field": "Rate Curve", "Value": str(cfg.get("rate_curve", "")), "Source": "Market Specific"})
        rec = cfg.get("rec_rate", 0)
        model_inputs.append({"Model Row": "-", "Field": "REC Rate", "Value": f"${rec}/MWh" if isinstance(rec, (int, float)) else str(rec), "Source": "Market Specific"})
        if model_inputs:
            st.dataframe(pd.DataFrame(model_inputs), use_container_width=True, hide_index=True)
    st.markdown('<div class="section-hdr">Full Market Comparison</div>', unsafe_allow_html=True)
    comp_rows = []
    for (s, u, p_), cfg_ in MARKET_CONFIGS.items():
        cma = cfg_.get('cma_blend')
        comp_rows.append({
            "State": s, "Utility": u, "Program": p_,
            "Incentive $/W": f"${cfg_.get('upfront_incentive', 0):.3f}" if cfg_.get('upfront_incentive') else "\u2014",
            "Cust Acq $/kWh": f"${cfg_.get('acq_blend', 0):.4f}" if cfg_.get('acq_blend') else "\u2014",
            "Cust Mgmt $/kWh": f"${cma:.5f}" if cma else "\u2014",
            "Blend Disc": f"{cfg_.get('disc_blend', 0):.0%}" if isinstance(cfg_.get('disc_blend'), (int, float)) else str(cfg_.get('disc_blend', '')) if cfg_.get('disc_blend') else "\u2014",
            "UCB": f"{cfg_.get('ucb', 0):.1%}" if cfg_.get('ucb') else "\u2014",
            "Rate Curve": cfg_.get("rate_curve", ""),
        })
    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True, height=400)


def tab_comparison(m1_projects, m2_projects, m1_label, m2_label, review_active, model_file,
                   mapper_projects=None):
    if not review_active or not model_file:
        st.markdown('<div style="text-align:center;padding:3rem;"><p style="font-size:0.95rem;font-weight:600;color:#212B48;">Upload models and press RUN REVIEW</p></div>', unsafe_allow_html=True)
        return

    active1 = {k: v for k, v in m1_projects.items() if v["toggle"]}
    active2 = {k: v for k, v in m2_projects.items() if v["toggle"]} if m2_projects else {}
    mapper_active = {k: v for k, v in (mapper_projects or {}).items() if v.get("toggle")}

    all_names_1 = {v["name"]: v for v in active1.values()}
    all_names_2 = {v["name"]: v for v in active2.values()}
    all_names_mapper = {v["name"]: v for v in mapper_active.values()}
    common = sorted(set(all_names_1.keys()) & set(all_names_2.keys()))

    # Pre-compute bible audit per anchor project (drives inline highlighting).
    # Audit runs against the Model 1 anchor data — that's the source of truth
    # being reviewed. Mapper deltas show on top of audit highlighting.
    _audit_cache = {}
    def _audit_for(name):
        if name in _audit_cache:
            return _audit_cache[name]
        proj = all_names_1.get(name)
        if not proj:
            _audit_cache[name] = None
            return None
        result = audit_project(proj["data"])
        _audit_cache[name] = result
        return result

    st.markdown(f"""
    <div class="kpi-row">
        {kpi_card(m1_label, str(len(all_names_1)), f"{sum(safe_float(p['data'].get(11)) or 0 for p in all_names_1.values()):.1f} MWdc", "accent")}
        {kpi_card(m2_label if m2_projects else "Model 2", str(len(all_names_2)) if all_names_2 else "\u2014", f"{sum(safe_float(p['data'].get(11)) or 0 for p in all_names_2.values()):.1f} MWdc" if all_names_2 else "Not loaded", "accent" if all_names_2 else "warn")}
        {kpi_card("Matched", str(len(common)), "By project name", "pass" if common else "teal")}
        {kpi_card("Dev Inputs", str(len(all_names_mapper)) if all_names_mapper else "\u2014", "From mapper output" if all_names_mapper else "Not loaded", "accent" if all_names_mapper else "warn")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-hdr">Project Selection</div>', unsafe_allow_html=True)
    sel_c1, sel_c2 = st.columns(2)
    with sel_c1:
        st.markdown(f"**Anchor Group** ({m1_label})")
        anchor_options = sorted(all_names_1.keys())
        anchor_sel = st.multiselect("Anchor projects", anchor_options, default=anchor_options, key="anchor_sel", label_visibility="collapsed")
    with sel_c2:
        if all_names_2:
            st.markdown(f"**Comparison Group** ({m2_label})")
            comp_options = sorted(all_names_2.keys())
            comp_sel = st.multiselect("Comparison projects", comp_options, default=comp_options, key="comp_sel", label_visibility="collapsed")
        else:
            st.markdown("**Comparison Group** (no Model 2)")
            comp_sel = []

    # FIX: Use st.session_state for compare_mode to prevent tab-reset on radio change
    ctrl_c1, ctrl_c2 = st.columns([2, 1])
    with ctrl_c1:
        compare_mode = st.radio("Compare as", ["Individual (matched)", "Group (weighted avg)"],
                                horizontal=True, key="cmp_mode",
                                help="Individual compares matched projects 1:1. Group computes MWdc-weighted avg of each selection.")
    with ctrl_c2:
        match_mode = st.radio("Display", ["Variance Only", "Full Matching"], horizontal=True, key="match_mode")

    VARIANCE_THRESHOLD = 0.000001

    def render_comparison_table(data1, data2, label1, label2, table_key):
        df_comp = build_comparison_table(data1, data2, "", label1, label2)
        display_cols = ["Row", "Field", label1, label2, "Delta", "\u0394 %"]
        df_display = df_comp[display_cols].copy()
        df_display = df_display.rename(columns={"Delta": "Delta (units)", "\u0394 %": "Delta (%)"})
        if match_mode == "Variance Only":
            df_display = df_display[
                df_comp["_delta_raw"].apply(lambda d: d is not None and abs(d) >= VARIANCE_THRESHOLD)
            ].reset_index(drop=True)
        st.dataframe(
            df_display.style.map(style_field_header, subset=["Field"]).map(style_delta, subset=["Delta (units)", "Delta (%)"]),
            use_container_width=True, hide_index=True, height=500)
        key_rows = [38, 33, 11, 12, 14, 118, 119, 122, 157, 158, 160, 216, 597, 602]
        delta_bars = []
        for _, row in df_comp.iterrows():
            if row["Row"] in key_rows and row.get("_delta_raw") is not None and abs(row["_delta_raw"]) >= VARIANCE_THRESHOLD:
                delta_bars.append({"Field": row["Field"], "Delta": row["_delta_raw"]})
        st.markdown("<br>", unsafe_allow_html=True)
        fig_db = build_delta_chart(delta_bars, label1, label2)
        if fig_db:
            st.plotly_chart(fig_db, use_container_width=True, key=f"delta_{table_key}")

    def _build_sidebyside_html(anchor_name, anchor_data, comp_list, variance_only=False):
        """Build an HTML table with frozen Row/Field/Anchor columns, delta columns, and scrollable comparisons.

        comp_list: list of (name, data_dict) tuples for comparison projects.
        Each comparison project gets a value column and a delta column.
        """
        from config import PCT_ROWS as _PCT_ROWS
        all_rows = [r for r in DISPLAY_ORDER if r in INPUT_ROW_LABELS or r in OUTPUT_ROWS]

        # Pre-compute all values and deltas
        table_rows = []
        for r in all_rows:
            label = INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}"))
            is_text = r in TEXT_ROWS or r in DATE_ROWS
            is_pct = r in _PCT_ROWS
            a_raw = anchor_data.get(r)
            a_num = safe_float(a_raw) if not is_text else None
            a_fmt = fmt_row_val(a_raw, r)

            comp_entries = []  # list of (formatted_val, formatted_delta, raw_delta)
            has_variance = False
            for cn, cd in comp_list:
                c_raw = cd.get(r)
                c_num = safe_float(c_raw) if not is_text else None
                c_fmt = fmt_row_val(c_raw, r)

                if not is_text and a_num is not None and c_num is not None:
                    raw_delta = c_num - a_num
                    if abs(raw_delta) >= VARIANCE_THRESHOLD:
                        has_variance = True
                        d_fmt = fmt_delta(raw_delta, is_pct)
                        neg_cls = ' class="neg-val"' if raw_delta < 0 else ''
                    else:
                        d_fmt = ""
                        neg_cls = ""
                        raw_delta = 0
                elif is_text and a_fmt != c_fmt:
                    has_variance = True
                    d_fmt = "\u2260"
                    neg_cls = ""
                    raw_delta = None
                else:
                    d_fmt = ""
                    neg_cls = ""
                    raw_delta = 0

                comp_entries.append((c_fmt, d_fmt, neg_cls))

            if variance_only and not has_variance:
                continue

            table_rows.append((r, label, a_fmt, comp_entries))

        # Build HTML
        comp_names = [cn for cn, _ in comp_list]
        n_comp = len(comp_names)

        hdr_cells = (
            '<th class="fr fr-row">Row</th>'
            '<th class="fr fr-field">Field</th>'
            f'<th class="fr fr-anchor anchor-border proj-hdr">{anchor_name}</th>'
        )
        for cn in comp_names:
            hdr_cells += f'<th class="proj-hdr">{cn}</th><th class="delta-hdr">\u0394</th>'

        body = ""
        prev_section = None
        n_extra = n_comp * 2  # value + delta per comp project
        for r, label, a_fmt, comp_entries in table_rows:
            # Section break
            sec = SECTION_BREAKS.get(r)
            if sec and sec != prev_section:
                prev_section = sec
                body += f'<tr class="sec-row"><td class="fr fr-row"></td><td class="fr fr-field">{sec}</td><td class="fr fr-anchor anchor-border"></td>'
                for _ in range(n_comp):
                    body += '<td></td><td class="delta-cell"></td>'
                body += '</tr>'

            # Bible-audit highlighting on the anchor cell
            audit_res = _audit_for(anchor_name)
            a_cls = status_class(audit_res, r)
            a_tip = status_tooltip(audit_res, r)
            a_attrs = (f' title="{a_tip}"' if a_tip else "")
            anchor_cls = f"fr fr-anchor anchor-border {a_cls}".rstrip()

            body += '<tr>'
            body += f'<td class="fr fr-row">{r}</td>'
            body += f'<td class="fr fr-field">{label}</td>'
            body += f'<td class="{anchor_cls}"{a_attrs}>{a_fmt}</td>'
            for c_fmt, d_fmt, neg_cls in comp_entries:
                body += f'<td>{c_fmt}</td>'
                body += f'<td class="delta-cell{" neg-val" if neg_cls else ""}">{d_fmt}</td>'
            body += '</tr>'

        legend = (
            '<div class="audit-legend">'
            '<span class="audit-chip audit-off">OFF bible</span>'
            '<span class="audit-chip audit-out">Out of range</span>'
            '<span class="audit-chip audit-missing">Missing</span>'
            '<span class="audit-chip audit-review">Manual review</span>'
            '</div>'
        )
        return legend + f'<div class="cmp-wrap"><table class="cmp-tbl"><thead><tr>{hdr_cells}</tr></thead><tbody>{body}</tbody></table></div>'

    if compare_mode == "Group (weighted avg)":
        anchor_projs = {k: v for k, v in active1.items() if v["name"] in anchor_sel}
        comp_projs = {k: v for k, v in active2.items() if v["name"] in comp_sel} if all_names_2 else {}
        if not anchor_sel:
            st.info("Select at least one Anchor project.")
        else:
            anchor_avg = compute_portfolio_wtd_avg(anchor_projs)
            comp_avg = compute_portfolio_wtd_avg(comp_projs) if comp_projs else None
            anchor_lbl = f"{m1_label} ({len(anchor_sel)}proj, {anchor_avg['_total_mw']:.1f}MW)"
            comp_lbl = f"{m2_label} ({len(comp_sel)}proj, {comp_avg['_total_mw']:.1f}MW)" if comp_avg else m2_label
            st.markdown(f'<div class="section-hdr">Group Comparison <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {anchor_lbl} vs {comp_lbl}</span></div>', unsafe_allow_html=True)
            if comp_avg:
                render_comparison_table(anchor_avg, comp_avg, anchor_lbl, comp_lbl, "group")
            else:
                st.info("Select Comparison projects from Model 2 to see deltas.")
    else:
        # Individual mode — single side-by-side table with frozen anchor
        if not anchor_sel:
            st.info("Select at least one Anchor project.")
        else:
            # First anchor project is the "main" project (frozen on left)
            anchor_name = anchor_sel[0]
            anchor_data = all_names_1[anchor_name]["data"]

            # Build comparison list: remaining anchors + all comp projects
            comp_projects = []
            for pn in anchor_sel[1:]:
                if pn in all_names_1:
                    comp_projects.append((f"{pn}", all_names_1[pn]["data"]))
            for pn in comp_sel:
                if pn in all_names_2:
                    comp_projects.append((f"{pn} ({m2_label})", all_names_2[pn]["data"]))

            # Append mapper (developer inputs) as a third source for the anchor
            # project — fuzzy match by substring since mapper names may include
            # site codes (e.g. "IL VER001 (US Highway 136)").
            if all_names_mapper:
                for mn, mp in all_names_mapper.items():
                    short = mn.split(" (")[0].strip()
                    if (anchor_name in mn or mn in anchor_name
                            or short in anchor_name or anchor_name in short):
                        comp_projects.append((f"{mn} (Dev Input)", mp["data"]))
                        break

            unmatched_anchor = [n for n in anchor_sel if n not in all_names_2 and n != anchor_name]
            unmatched_comp = [n for n in comp_sel if n not in all_names_1] if comp_sel else []
            if unmatched_anchor:
                st.caption(f"**{m1_label} only (no M2 match):** {', '.join(unmatched_anchor)}")
            if unmatched_comp:
                st.caption(f"**{m2_label} only (no M1 match):** {', '.join(unmatched_comp)}")

            is_variance = match_mode == "Variance Only"
            st.markdown(f'<div class="section-hdr">Project Comparison <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 Anchor: {anchor_name}</span></div>', unsafe_allow_html=True)
            html = _build_sidebyside_html(anchor_name, anchor_data, comp_projects, variance_only=is_variance)
            st.markdown(html, unsafe_allow_html=True)

    # --- Downloads (single-click) ---
    st.markdown('<div class="section-hdr">Download Report</div>', unsafe_allow_html=True)
    first_anchor = anchor_sel[0] if anchor_sel else "Portfolio"

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.markdown("**Excel (Variance + Full sheets)**")
        if compare_mode == "Group (weighted avg)" and anchor_sel:
            a_projs = {k: v for k, v in active1.items() if v["name"] in anchor_sel}
            c_projs = {k: v for k, v in active2.items() if v["name"] in comp_sel} if all_names_2 else {}
            a_avg = compute_portfolio_wtd_avg(a_projs)
            c_avg = compute_portfolio_wtd_avg(c_projs) if c_projs else {}
            xl_label1 = f"{m1_label} (Wtd Avg)"
            xl_label2 = f"{m2_label} (Wtd Avg)" if c_avg else "\u2014"
            export_rows = build_export_rows(a_avg, c_avg if c_avg else None, xl_label1, xl_label2)
            xl_title = f"{m1_label} vs {m2_label} \u2014 Group Comparison"
            xlsx_buf = generate_comparison_xlsx(export_rows, xl_label1, xl_label2, xl_title)
            xl_filename = f"38DN_Comparison_{first_anchor.replace(' ', '_')}.xlsx"
        else:
            # Individual mode: collect all matched projects for multi-project export
            matched_for_export = [n for n in anchor_sel if n in all_names_2 and n in comp_sel] if comp_sel else []
            if len(matched_for_export) > 1:
                # Multi-project export with Summary + per-project Variance/Full sheets
                projects_data = []
                for pn in matched_for_export:
                    d1 = all_names_1[pn]["data"]
                    c_proj_e = all_names_2.get(pn, {})
                    d2 = c_proj_e.get("data") if isinstance(c_proj_e, dict) and "data" in c_proj_e else c_proj_e
                    projects_data.append((pn, d1, d2))
                xl_label1, xl_label2 = m1_label, m2_label
                xl_title = f"{m1_label} vs {m2_label} \u2014 {len(matched_for_export)} Projects"
                xlsx_buf = generate_multi_project_xlsx(projects_data, xl_label1, xl_label2, xl_title)
                xl_filename = f"38DN_Comparison_Multi_{len(matched_for_export)}proj.xlsx"
            else:
                # Single project (or no match) - original behaviour
                a_data = all_names_1[first_anchor]["data"] if first_anchor in all_names_1 else {}
                c_proj_e = all_names_2.get(first_anchor, {})
                c_data = c_proj_e.get("data") if isinstance(c_proj_e, dict) and "data" in c_proj_e else c_proj_e
                xl_label1, xl_label2 = m1_label, m2_label if c_data else "\u2014"
                export_rows = build_export_rows(a_data, c_data if c_data else None, xl_label1, xl_label2)
                xl_title = f"{first_anchor} \u2014 {m1_label} vs {m2_label}"
                xlsx_buf = generate_comparison_xlsx(export_rows, xl_label1, xl_label2, xl_title)
                xl_filename = f"38DN_Comparison_{first_anchor.replace(' ', '_')}.xlsx"

        st.download_button(
            label="\u2B07 Download .xlsx", data=xlsx_buf,
            file_name=xl_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx",
        )

    with dl2:
        st.markdown("**PowerPoint (summary + category slides)**")
        cmp_bible = st.checkbox("Include Bible comparison", value=False, key="cmp_bible")
        anchor_data = all_names_1[first_anchor]["data"] if first_anchor in all_names_1 else {}
        comp_data_pptx = all_names_2.get(first_anchor, {})
        comp_data_pptx = comp_data_pptx.get("data") if isinstance(comp_data_pptx, dict) and "data" in comp_data_pptx else comp_data_pptx
        buf = generate_pptx(
            proj_name=first_anchor,
            proj1_data=anchor_data,
            proj2_data=comp_data_pptx if comp_data_pptx else None,
            m1_label=m1_label, m2_label=m2_label,
            compare_bible=cmp_bible,
            compare_model=bool(comp_data_pptx),
        )
        st.download_button(
            label="\u2B07 Download .pptx", data=buf,
            file_name=f"38DN_Review_{first_anchor.replace(' ', '_')}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="dl_pptx",
        )

    with dl3:
        st.markdown("**PDF (single-page summary)**")
        anchor_data_pdf = all_names_1[first_anchor]["data"] if first_anchor in all_names_1 else {}
        comp_data_pdf = all_names_2.get(first_anchor, {})
        comp_data_pdf = comp_data_pdf.get("data") if isinstance(comp_data_pdf, dict) and "data" in comp_data_pdf else comp_data_pdf
        pdf_buf = generate_pdf(
            proj_name=first_anchor,
            proj1_data=anchor_data_pdf,
            proj2_data=comp_data_pdf if comp_data_pdf else None,
            m1_label=m1_label, m2_label=m2_label,
        )
        st.download_button(
            label="\u2B07 Download .pdf", data=pdf_buf,
            file_name=f"38DN_Summary_{first_anchor.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="dl_pdf",
        )


def tab_review(m1_projects, m1_ops, m1_label, m2_label, model_file, model_file_2, review_active,
               rate_curves=None, gh25_ref=None, dr_files=None):
    if not model_file or not review_active:
        msg = "Press RUN REVIEW in the sidebar" if model_file else "Upload a Pricing Model to begin"
        st.markdown(f'<div style="text-align:center;padding:3rem 2rem;"><p style="font-size:0.95rem;font-weight:600;color:#212B48;">{msg}</p></div>', unsafe_allow_html=True)
        return

    projects = m1_projects
    ops_sandbox = m1_ops
    active = {k: v for k, v in projects.items() if v["toggle"]}
    inactive = {k: v for k, v in projects.items() if not v["toggle"]}
    if not active:
        st.error("No projects toggled **On** in Row 7.")
        return

    selected_names = st.multiselect("Active Projects", [v["name"] for v in active.values()],
                                    default=[v["name"] for v in active.values()], label_visibility="collapsed")
    selected = {k: v for k, v in active.items() if v["name"] in selected_names}
    if not selected:
        return

    all_findings = {}
    for col_idx, proj in selected.items():
        findings, state = validate_project(proj["data"], BIBLE_BENCHMARKS)
        all_findings[proj["name"]] = {"findings": findings, "state": state, "data": proj["data"]}

    total_mw = sum(safe_float(p["data"].get(11)) or 0 for p in selected.values())
    avg_npp = [v for v in (safe_float(p["data"].get(38)) for p in selected.values()) if v is not None and v != 0]
    tc = sum(len(af["findings"]) for af in all_findings.values())
    tf = sum(1 for af in all_findings.values() for f in af["findings"] if f["Status"] in ("LOW", "HIGH"))
    tw = sum(1 for af in all_findings.values() for f in af["findings"] if f["Status"] == "WARNING")

    st.markdown(f'<div class="kpi-row">{kpi_card("Active Projects", str(len(selected)), f"{len(inactive)} inactive", "accent")}{kpi_card("Portfolio Size", f"{total_mw:.1f} MW", "Total MWDC", "accent")}{kpi_card("Avg NPP", fmt_dollar_w(sum(avg_npp) / len(avg_npp) if avg_npp else None), "$/W", "accent")}{kpi_card("Checks Passed", f"{tc - tf - tw}/{tc}", "", "pass" if tf == 0 else "fail")}{kpi_card("Flags", str(tf), f"{tw} missing", "fail" if tf else "pass")}</div>', unsafe_allow_html=True)

    # Project summary table
    st.markdown('<div class="section-hdr">Project Summary</div>', unsafe_allow_html=True)
    rows = []
    for pn, af in all_findings.items():
        d = af["data"]
        ok = sum(1 for f in af["findings"] if f["Status"] == "OK")
        fl = sum(1 for f in af["findings"] if f["Status"] in ("LOW", "HIGH"))
        wn = sum(1 for f in af["findings"] if f["Status"] == "WARNING")
        rows.append({"Project": pn, "State": str(d.get(18, "")), "MW(DC)": safe_float(d.get(11)),
                     "EPC($/W)": safe_float(d.get(118)), "PPA($/kWh)": safe_float(d.get(157)),
                     "NPP($/W)": safe_float(d.get(38)), "FMV($/W)": safe_float(d.get(33)),
                     "ITC%": safe_float(d.get(597)), "Pass": ok, "Flags": fl, "Missing": wn})
    df_s = pd.DataFrame(rows)
    st.dataframe(df_s.style.format({
        "MW(DC)": "{:.2f}", "EPC($/W)": "${:.3f}", "PPA($/kWh)": "${:.4f}",
        "NPP($/W)": lambda x: fmt_dollar_w(x), "FMV($/W)": "${:.3f}",
        "ITC%": lambda x: f"{x:.0%}" if x else "\u2014",
    }, na_rep="\u2014").map(style_flag, subset=["Flags"]).map(style_warn, subset=["Missing"]),
        use_container_width=True, hide_index=True)

    # Customer Acquisition & Management conversions
    with st.expander("Customer Acquisition & Management \u2014 Unit Conversions", expanded=False):
        cma_rows = []
        for col_idx, proj in selected.items():
            d = proj["data"]
            yield_kwh_wdc = safe_float(d.get(14))
            cust_acq_w = safe_float(d.get(121))
            cust_mgmt_w = safe_float(d.get(240))
            acq_kwh = cust_acq_w / yield_kwh_wdc if cust_acq_w and yield_kwh_wdc else None
            acq_mwh = acq_kwh * 1000 if acq_kwh is not None else None
            mgmt_kwh = cust_mgmt_w / (yield_kwh_wdc * 1_000_000) if cust_mgmt_w and yield_kwh_wdc else None
            mgmt_mwh = mgmt_kwh * 1000 if mgmt_kwh is not None else None
            cma_rows.append({
                "Project": proj["name"],
                "Yield (kWh/Wdc)": f"{yield_kwh_wdc:.4f}" if yield_kwh_wdc else "\u2014",
                "Cust Acq ($/W)": f"${cust_acq_w:.4f}" if cust_acq_w else "\u2014",
                "Cust Acq ($/kWh)": f"${acq_kwh:.5f}" if acq_kwh else "\u2014",
                "Cust Mgmt ($/MW/yr)": f"${cust_mgmt_w:,.0f}" if cust_mgmt_w else "\u2014",
                "Cust Mgmt ($/kWh)": f"${mgmt_kwh:.5f}" if mgmt_kwh else "\u2014",
            })
        if cma_rows:
            st.dataframe(pd.DataFrame(cma_rows), use_container_width=True, hide_index=True)
            st.caption("Conversions: $/kWh = $/W \u00F7 Yield(kWh/Wdc) | $/MW/yr \u00F7 (Yield \u00D7 1M W/MW) = $/kWh")

    # Per-project findings
    for pn, af in all_findings.items():
        with st.expander(f"{pn} \u2014 {af['state']}", expanded=len(all_findings) == 1):
            df_f = pd.DataFrame(af["findings"])
            for cat in BIBLE_BENCHMARKS:
                cat_df = df_f[df_f["Category"] == cat].copy()
                if cat_df.empty:
                    continue
                fl = sum(cat_df["Status"].isin(["LOW", "HIGH"]))
                wn = sum(cat_df["Status"] == "WARNING")
                tag = (f' <span class="badge badge-fail">{fl} FLAGGED</span>' if fl else
                       f' <span class="badge badge-warn">{wn} MISSING</span>' if wn else
                       ' <span class="badge badge-ok">ALL PASS</span>')
                st.markdown(f'<div class="section-hdr">{cat}{tag}</div>', unsafe_allow_html=True)
                disp = cat_df[["Check", "Row", "Value", "Min", "Max", "Unit", "Status", "Note"]].copy()
                disp["Value"] = disp["Value"].apply(lambda v: f"{v:.3f}" if isinstance(v, float) else ("\u2014" if v is None else str(v)))
                disp["Min"] = disp["Min"].apply(lambda v: f"{v:.3f}" if isinstance(v, float) else str(v))
                disp["Max"] = disp["Max"].apply(lambda v: f"{v:.3f}" if isinstance(v, float) else str(v))
                st.dataframe(disp.style.map(style_status, subset=["Status"]), use_container_width=True, hide_index=True)

    # Rate Component Detail
    st.markdown('<div class="section-hdr">Rate Component Detail by Project</div>', unsafe_allow_html=True)
    for col_idx, proj in selected.items():
        rcs = proj.get("rate_comps", {})
        if not rcs:
            continue
        with st.expander(f"{proj['name']} \u2014 Rate Components", expanded=False):
            for section, label, toggle_key in [
                ("Equity", "Revenue Rate Components for Equity Model", "equity_on"),
                ("Debt", "Revenue Rate Components for Debt Model", "debt_on"),
                ("Appraisal", "Revenue Rate Components for Appraisal Model", "appraisal_on"),
            ]:
                active_comps = [i for i in range(1, 7) if rcs.get(i, {}).get(toggle_key)]
                if not active_comps:
                    continue
                with st.expander(f"{section} \u2014 {len(active_comps)} active components", expanded=(section == "Equity")):
                    comp_rows = []
                    for i in active_comps:
                        rc = rcs[i]
                        sd = rc.get("start_date")
                        sd_str = sd.strftime("%Y-%m-%d") if hasattr(sd, "strftime") else str(sd or "\u2014")
                        comp_rows.append({
                            "Comp": i, "Name": str(rc.get("name") or "\u2014"),
                            "Type": str(rc.get("custom_generic") or "\u2014"),
                            "Rate ($/kWh)": f"${safe_float(rc.get('energy_rate')) or 0:.4f}",
                            "Escalator": f"{safe_float(rc.get('escalator')) or 0:.2%}",
                            "Start": sd_str,
                            "Term (yrs)": str(rc.get("term") or "\u2014"),
                            "Discount": f"{safe_float(rc.get('discount')) or 0:.1%}",
                            "UCB Fee": f"{safe_float(rc.get('ucb_fee')) or 0:.1%}",
                        })
                    st.dataframe(pd.DataFrame(comp_rows).style.map(style_field_header, subset=["Name"]),
                                 use_container_width=True, hide_index=True)

    # DSCR Schedule
    st.markdown('<div class="section-hdr">DSCR Schedule by Project</div>', unsafe_allow_html=True)
    for col_idx, proj in selected.items():
        dscr = proj.get("dscr_schedule", {})
        if not dscr:
            continue
        dscr_lbl = proj.get("dscr_label")
        lev_type = proj["data"].get("_front_back_toggle", "")
        sizing = proj["data"].get("_debt_sizing_method", "")
        subtitle_parts = [str(x) for x in [lev_type, sizing, f"DSRA: {dscr_lbl}" if dscr_lbl else None] if x]
        with st.expander(f"{proj['name']} \u2014 {' | '.join(subtitle_parts)}", expanded=False):
            st.dataframe(pd.DataFrame([{"Year": yr, "DSCR": f"{v:.2f}x"} for yr, v in sorted(dscr.items())]),
                         use_container_width=True, hide_index=True, height=200)

    # Ops Sandbox
    if ops_sandbox and (ops_sandbox.get("revenue_adders") or ops_sandbox.get("opex_overrides")):
        live_proj = ops_sandbox.get("live_project", "")
        live_name = " | ".join(l.strip() for l in str(live_proj).splitlines() if l.strip()) if live_proj else "Active Project"
        st.markdown(f'<div class="section-hdr">Ops Sandbox Overrides <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {live_name}</span></div>', unsafe_allow_html=True)
        if ops_sandbox.get("revenue_adders"):
            with st.expander("Custom Revenue Adders", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Label": a["label"],
                    "Annual $": f"${a['annual']:,.0f}" if a.get("annual") else "\u2014",
                    "Equity": "On" if a["equity"] else "Off",
                    "Debt": "On" if a["debt"] else "Off",
                    "Appraisal": "On" if a["appraisal"] else "Off",
                    "NPV Total": f"${a['npv_total']:,.0f}" if a.get("npv_total") else "\u2014",
                } for a in ops_sandbox["revenue_adders"]]), use_container_width=True, hide_index=True)
        if ops_sandbox.get("opex_overrides"):
            with st.expander("Custom OpEx Overrides", expanded=False):
                st.dataframe(pd.DataFrame([{
                    "Label": o["label"],
                    "Annual $": f"${o['annual']:,.0f}" if o.get("annual") else "\u2014",
                    "Equity": "On" if o["equity"] else "Off",
                    "Debt": "On" if o["debt"] else "Off",
                    "Appraisal": "On" if o["appraisal"] else "Off",
                    "NPV Total": f"${o['npv_total']:,.0f}" if o.get("npv_total") else "\u2014",
                } for o in ops_sandbox["opex_overrides"]]), use_container_width=True, hide_index=True)

    # Cross-project anomaly map
    if len(selected) > 1:
        st.markdown('<div class="section-hdr">Cross-Project Anomaly Map</div>', unsafe_allow_html=True)
        heat = {}
        for pn, af in all_findings.items():
            for f in af["findings"]:
                heat.setdefault(f["Check"], {})[pn] = {"OK": 0, "WARNING": 1, "LOW": 2, "HIGH": 2}.get(f["Status"], 0)
        df_h = pd.DataFrame(heat).T
        fig = px.imshow(df_h.values, x=df_h.columns.tolist(), y=df_h.index.tolist(),
                        color_continuous_scale=[[0, "rgba(69,167,80,0.1)"], [0.5, "#eef0f5"], [1, "#c45050"]],
                        labels={"color": "Severity"}, aspect="auto")
        fig.update_layout(coloraxis_showscale=False, height=max(280, len(heat) * 30),
                          margin=dict(l=180, t=20, b=20, r=20),
                          font=dict(family="DM Sans", size=12), plot_bgcolor=PLOTLY_BG, paper_bgcolor=PLOTLY_BG)
        st.plotly_chart(fig, use_container_width=True, key="heatmap")

    # --- Bible Review Download ---
    st.markdown('<div class="section-hdr">Download Bible Review Report</div>', unsafe_allow_html=True)
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.markdown("**Excel — Per-Project Bible Review + Rate Curves**")
        st.caption("Individual project sheets with Bible comparison, flagged variations, and rate curve analysis vs GH25")
        review_buf = generate_review_xlsx(
            projects=projects,
            bible_benchmarks=BIBLE_BENCHMARKS,
            rate_curves=rate_curves,
            gh25_ref=gh25_ref,
            data_room=None,
            model_label=m1_label,
        )
        active_count = len([v for v in projects.values() if v["toggle"]])
        st.download_button(
            label=f"\u2B07 Download Bible Review ({active_count} projects)",
            data=review_buf,
            file_name=f"38DN_Bible_Review_{m1_label.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_review_xlsx",
        )
    with dl_col2:
        if gh25_ref:
            st.markdown("**Rate curves included:**")
            curves_avail = list(gh25_ref.get("annual", {}).keys())
            st.caption(f"GH25 reference curves: {', '.join(curves_avail)}")
            for cn, cagr in gh25_ref.get("cagrs", {}).items():
                if cagr:
                    st.caption(f"  {cn} CAGR: {cagr:.2%}")
        else:
            st.caption("GH25 reference file not found — rate curve analysis unavailable")


def tab_value_drivers(m1_projects, m1_label, m2_label, model_file, model_file_2, review_active):
    if not model_file or not review_active:
        st.info("Upload a Pricing Model and press RUN REVIEW first.")
        return
    sel = {k: v for k, v in m1_projects.items() if v["toggle"]}
    comp_basis = f"{m1_label}" if not model_file_2 else f"{m1_label} vs {m2_label}"
    st.markdown(f'<div class="section-hdr">CapEx Waterfall & Value Drivers <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {comp_basis}</span></div>', unsafe_allow_html=True)
    for ci, proj in sel.items():
        st.markdown(f"**{proj['name']}**")
        c1, c2 = st.columns(2)
        with c1:
            fig = build_capex_waterfall(proj["data"], proj["name"])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"wf_{ci}")
        with c2:
            fig = build_value_driver_chart(proj["data"], proj["name"])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"vd_{ci}")
        st.markdown(f'<div class="section-hdr" style="font-size:14px;margin-top:8px;">Sensitivity Analysis (\u00b110% Input Variation) <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {proj["name"]}</span></div>', unsafe_allow_html=True)
        fig_tornado = build_sensitivity_tornado(proj["data"], proj["name"])
        if fig_tornado:
            st.plotly_chart(fig_tornado, use_container_width=True, key=f"tornado_{ci}")

    st.markdown(f'<div class="section-hdr">Development Fee Comparison <span style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 {comp_basis}</span></div>', unsafe_allow_html=True)
    dev_fees = [{"Project": p["name"], "Dev Fee ($/W)": safe_float(p["data"].get(32))} for p in sel.values() if safe_float(p["data"].get(32)) is not None]
    if dev_fees:
        df_dev = pd.DataFrame(dev_fees)
        fig = go.Figure(go.Bar(
            x=df_dev["Project"], y=df_dev["Dev Fee ($/W)"],
            marker_color=CHART_COLORS[:len(dev_fees)], marker_line=dict(width=0),
            text=[f"${v:.3f}" for v in df_dev["Dev Fee ($/W)"]],
            textposition="outside", textfont=dict(family="Century Gothic, DM Sans", size=12, color=P["text"]),
        ))
        fig.update_layout(yaxis_title="$/W", showlegend=False,
                          title=dict(text="<b>Development Fee Comparison</b>", font=dict(size=14, color=P["navy"])),
                          xaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(styled_plotly(fig, 350), use_container_width=True, key="devfee_comp")


def tab_raw_data(m1_projects, dr_files, model_file, review_active):
    if not model_file or not review_active:
        st.info("Upload a Pricing Model and press RUN REVIEW first.")
        return
    sel = {k: v for k, v in m1_projects.items() if v["toggle"]}
    st.markdown('<div class="section-hdr">Full Input Matrix</div>', unsafe_allow_html=True)
    ar = sorted(set(INPUT_ROW_LABELS.keys()) | set(OUTPUT_ROWS.keys()))
    rr = []
    for r in ar:
        rd = {"Row": r, "Field": INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}"))}
        for proj in sel.values():
            rd[proj["name"]] = proj["data"].get(r, "")
        rr.append(rd)
    st.dataframe(pd.DataFrame(rr), use_container_width=True, hide_index=True, height=650)

    dr_data = load_data_room(dr_files) if dr_files else None
    if dr_data:
        st.markdown('<div class="section-hdr">Developer Data Room</div>', unsafe_allow_html=True)
        for fn, info in dr_data.items():
            with st.expander(f"{fn} ({len(info['sheets'])} sheets)"):
                for sn in info["sheets"]:
                    st.markdown(f"**{sn}**")
                    sr = info["data"].get(sn, [])
                    if sr:
                        st.dataframe(pd.DataFrame(sr[:30]), use_container_width=True, hide_index=True)


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

    # Load data once
    m1_projects, m2_projects, m1_ops = {}, {}, {}
    m1_rate_curves, gh25_ref = {}, {}
    mapper_projects = {}
    if review_active and has_any_model:
        # Model 1: prefer uploaded file, fall back to macro runner
        if model_file:
            m1_result = load_pricing_model(model_file)
        elif has_mr_m1:
            m1_result = mr_model
            m1_label = mr_label
        else:
            m1_result = None

        # Model 2: prefer uploaded file, fall back to macro runner
        if model_file_2:
            m2_result = load_pricing_model(model_file_2)
        elif has_mr_m2:
            m2_result = mr_model
            m2_label = mr_label
        else:
            m2_result = None

        m1_projects = get_projects(m1_result) if m1_result else {}
        m2_projects = get_projects(m2_result) if m2_result else {}
        mapper_projects = load_mapper_output(mapper_file) if mapper_file else {}
        m1_ops = get_ops_sandbox(m1_result) if m1_result else {}
        m1_rate_curves = get_rate_curves(m1_result) if m1_result else {}

        # Load GH25 reference curves (cached at session level)
        if "gh25_ref" not in st.session_state:
            _gh25_path = Path(r"C:\Users\CarolineZepecki\Desktop\GH_IL_Summer 2025_OBBB_38 Degrees.xlsx")
            st.session_state["gh25_ref"] = load_gh25_reference(str(_gh25_path)) if _gh25_path.exists() else {}
        gh25_ref = st.session_state.get("gh25_ref", {})

    # For tab guard checks: use a truthy sentinel when macro runner is the source
    effective_m1 = model_file if model_file else (mr_label if has_mr_m1 else None)
    effective_m2 = model_file_2 if model_file_2 else (mr_label if has_mr_m2 else None)

    tabs = ["MODEL REVIEW", "MODEL COMPARISON", "PORTFOLIO VIEW", "PRICING BIBLE Q1 '26",
            "MARKET ASSUMPTIONS", "VALUE DRIVERS", "RAW DATA"]
    t_review, t_compare, t_portfolio, t_bible, t_market, t_charts, t_raw = st.tabs(tabs)

    with t_portfolio:
        tab_portfolio(m1_projects, m2_projects, m1_label, m2_label, effective_m2, review_active, effective_m1)
    with t_bible:
        tab_bible()
    with t_market:
        tab_market()
    with t_compare:
        tab_comparison(m1_projects, m2_projects, m1_label, m2_label, review_active, effective_m1,
                       mapper_projects=mapper_projects)
    with t_review:
        tab_review(m1_projects, m1_ops, m1_label, m2_label, effective_m1, effective_m2, review_active,
                  rate_curves=m1_rate_curves, gh25_ref=gh25_ref, dr_files=dr_files)
    with t_charts:
        tab_value_drivers(m1_projects, m1_label, m2_label, effective_m1, effective_m2, review_active)
    with t_raw:
        tab_raw_data(m1_projects, dr_files, effective_m1, review_active)


if __name__ == "__main__":
    main()
