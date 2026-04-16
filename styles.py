"""
38DN Pricing Model Review — CSS Styles
Intent: Dense financial review tool. Precise, legible, terminal-adjacent.
Palette: 38DN navy/teal/blue brand. Green = semantic pass only. Red = flags.
"""

APP_CSS = """
<style>
:root {
    --text-primary: #050D25;
    --text-secondary: #212B48;
    --text-tertiary: #518484;
    --text-muted: #7a8291;
    --surface-base: #ffffff;
    --surface-raised: #f6f7f9;
    --surface-inset: #eef0f5;
    --surface-overlay: #ffffff;
    --border-subtle: rgba(5,13,37,0.06);
    --border-default: rgba(5,13,37,0.10);
    --border-emphasis: rgba(5,13,37,0.18);
    --border-strong: rgba(33,43,72,0.25);
    --brand-navy: #050D25;
    --brand-indigo: #212B48;
    --brand-green: #45A750;
    --brand-teal: #518484;
    --brand-blue: #1D6FA9;
    --status-pass: #3a7d44;
    --status-pass-bg: rgba(69,167,80,0.08);
    --status-fail: #b83230;
    --status-fail-bg: rgba(184,50,48,0.06);
    --status-warn: #518484;
    --status-warn-bg: rgba(81,132,132,0.08);
}

html, body, [class*="css"] {
    font-family: 'Century Gothic', 'Segoe UI', system-ui, sans-serif;
    color: var(--text-primary);
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
}
h1,h2,h3,h4,h5,h6 {
    font-family: 'Century Gothic', 'Segoe UI', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
    color: var(--text-primary) !important;
}

.block-container { padding-top: 1.2rem; max-width: 1400px; }

.hero-banner {
    background: linear-gradient(135deg, #050D25 0%, #0d1a38 40%, #1a2340 70%, #212B48 100%);
    border-radius: 4px;
    padding: 0.9rem 1.4rem;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid #518484;
    box-shadow: 0 1px 3px rgba(5,13,37,0.12);
}
.hero-banner h1 {
    color: #ffffff !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
    letter-spacing: 0.06em;
    font-weight: 700 !important;
    text-transform: uppercase;
}
.hero-banner p {
    color: rgba(255,255,255,0.45);
    font-size: 0.7rem;
    margin: 0.15rem 0 0 0;
    letter-spacing: 0.03em;
}

.kpi-row {
    display: flex;
    gap: 0.6rem;
    margin: 0.6rem 0 1rem 0;
    flex-wrap: wrap;
}
.kpi-card {
    flex: 1;
    min-width: 130px;
    background: var(--surface-base);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    padding: 0.6rem 0.8rem;
}
.kpi-card .kpi-label {
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    margin-bottom: 0.15rem;
}
.kpi-card .kpi-value {
    font-family: 'Century Gothic', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
}
.kpi-card .kpi-sub {
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}
.kpi-card.accent { border-left: 2.5px solid var(--brand-blue); }
.kpi-card.pass   { border-left: 2.5px solid var(--brand-green); }
.kpi-card.warn   { border-left: 2.5px solid var(--brand-teal); }
.kpi-card.fail   { border-left: 2.5px solid var(--status-fail); }
.kpi-card.teal   { border-left: 2.5px solid var(--brand-teal); }

.badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    font-family: 'Century Gothic', sans-serif;
    letter-spacing: 0.04em;
}
.badge-ok   { background: var(--status-pass-bg); color: var(--status-pass); border: 1px solid rgba(69,167,80,0.15); }
.badge-warn { background: var(--status-warn-bg); color: var(--status-warn); border: 1px solid rgba(81,132,132,0.15); }
.badge-fail { background: var(--status-fail-bg); color: var(--status-fail); border: 1px solid rgba(184,50,48,0.12); }

.section-hdr {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-tertiary);
    border-bottom: 1px solid var(--border-emphasis);
    padding-bottom: 0.35rem;
    margin: 1.2rem 0 0.6rem 0;
}

.note-box {
    background: var(--surface-inset);
    border-left: 2px solid var(--brand-teal);
    padding: 0.5rem 0.8rem;
    border-radius: 0 3px 3px 0;
    font-size: 0.76rem;
    margin: 0.35rem 0;
    color: var(--text-secondary);
}

[data-testid="stSidebar"] {
    background: var(--surface-raised) !important;
    border-right: 1px solid var(--border-default);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--text-primary) !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.03em;
}
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stFileUploader label,
[data-testid="stSidebar"] .stNumberInput label {
    font-size: 0.72rem !important;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
    margin: 0.6rem 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border-emphasis);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Century Gothic', sans-serif;
    font-weight: 600;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
    padding: 0.5rem 0.9rem;
    color: var(--text-muted);
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--brand-teal) !important;
    color: var(--brand-teal) !important;
}

span[data-baseweb="tag"] {
    background-color: rgba(81,132,132,0.12) !important;
    border-color: rgba(81,132,132,0.3) !important;
    color: #3d6868 !important;
}
span[data-baseweb="tag"] > span:first-child {
    color: #3d6868 !important;
}
div[data-baseweb="select"] [aria-selected="true"],
li[aria-selected="true"] {
    background-color: rgba(81,132,132,0.08) !important;
}
div[data-baseweb="input"] [data-focused="true"],
div[data-baseweb="select"] > div:focus-within {
    border-color: #518484 !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #518484 !important;
    box-shadow: 0 0 0 1px rgba(81,132,132,0.2) !important;
}

.stDataFrame { font-size: 0.82rem; }
.stDataFrame th { font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.03em; }

.streamlit-expanderHeader { font-size: 0.82rem !important; font-weight: 600; }

.neg { color: var(--status-fail); }

/* Side-by-side comparison table with frozen anchor */
.cmp-wrap {
    overflow-x: auto;
    overflow-y: auto;
    max-height: 620px;
    border: 1px solid var(--border-default);
    border-radius: 4px;
    background: #fff;
}
.cmp-tbl {
    border-collapse: separate;
    border-spacing: 0;
    font-family: 'Century Gothic', 'Segoe UI', sans-serif;
    font-size: 0.82rem;
    white-space: nowrap;
    width: max-content;
    min-width: 100%;
}
.cmp-tbl th, .cmp-tbl td {
    padding: 3px 12px;
    border-bottom: 1px solid #eef0f5;
    text-align: center;
    vertical-align: middle;
}
.cmp-tbl thead th {
    background: var(--surface-raised);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-weight: 700;
    color: var(--text-secondary);
    position: sticky;
    top: 0;
    z-index: 10;
    border-bottom: 2px solid var(--border-emphasis);
}
.cmp-tbl thead th.proj-hdr {
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--text-primary);
}
/* Frozen columns */
.cmp-tbl .fr { position: sticky; z-index: 5; background: #fff; }
.cmp-tbl thead .fr { z-index: 15; background: var(--surface-raised); }
.cmp-tbl .fr-row { left: 0; min-width: 42px; max-width: 42px; color: var(--text-muted); font-size: 0.72rem; }
.cmp-tbl .fr-field { left: 42px; min-width: 210px; text-align: left; font-weight: 700; color: var(--text-primary); }
.cmp-tbl .fr-anchor { left: 252px; min-width: 110px; }
/* Thick separator between anchor and comparisons */
.cmp-tbl .anchor-border { border-right: 3px solid #D9D9D9; }
/* Alternating rows */
.cmp-tbl tbody tr:nth-child(even) td { background: var(--surface-raised); }
.cmp-tbl tbody tr:nth-child(even) .fr { background: var(--surface-raised); }
/* Section break rows */
.cmp-tbl .sec-row td { font-weight: 700; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-tertiary); border-bottom: 2px solid var(--border-emphasis); padding-top: 10px; }
/* Delta column styling */
.cmp-tbl .delta-hdr { font-size: 0.62rem; color: var(--text-muted); min-width: 80px; }
.cmp-tbl .delta-cell { font-style: italic; color: var(--text-muted); font-size: 0.78rem; }
.cmp-tbl .delta-cell.neg-val { color: var(--status-fail); font-weight: 600; }

/* ===== Bible-audit inline cell highlighting =====
   Applied to the anchor (Model 1) cell when the project's input deviates
   from the Q1 '26 Pricing Bible canonical value. Hover the cell for the
   tooltip with expected value & reason. */
.cmp-tbl .audit-off     { background: rgba(184, 50, 48, 0.16) !important;  color: #7a1f1d; font-weight: 700; box-shadow: inset 3px 0 0 #b83230; }
.cmp-tbl .audit-out     { background: rgba(245, 196, 60, 0.22) !important; color: #6e4c08; font-weight: 700; box-shadow: inset 3px 0 0 #f5c43c; }
.cmp-tbl .audit-missing { background: rgba(120, 130, 145, 0.14) !important; color: #4a525e; font-style: italic; box-shadow: inset 3px 0 0 #788291; }
.cmp-tbl .audit-review  { background: rgba(29, 111, 169, 0.12) !important;  color: #144a72; font-weight: 600; box-shadow: inset 3px 0 0 #1D6FA9; }

.audit-legend {
    display: flex; gap: 0.5rem; margin: 0.4rem 0 0.6rem 0;
    font-size: 0.7rem; flex-wrap: wrap; align-items: center;
}
.audit-legend::before {
    content: "Bible audit:"; font-weight: 700; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em; margin-right: 0.25rem;
}
.audit-chip {
    padding: 0.18rem 0.5rem; border-radius: 4px; font-weight: 600;
    border: 1px solid rgba(0,0,0,0.06); white-space: nowrap;
}
.audit-chip.audit-off     { background: rgba(184, 50, 48, 0.16);  color: #7a1f1d; }
.audit-chip.audit-out     { background: rgba(245, 196, 60, 0.22); color: #6e4c08; }
.audit-chip.audit-missing { background: rgba(120, 130, 145, 0.14); color: #4a525e; }
.audit-chip.audit-review  { background: rgba(29, 111, 169, 0.12);  color: #144a72; }
</style>
"""

SIDEBAR_CHECKBOX_CSS = """
<style>
div[data-testid="stSidebar"] .stCheckbox span[data-testid="stCheckboxLabel"] {
    font-size: 0.82rem !important; font-weight: 700 !important;
    font-family: 'Century Gothic', sans-serif !important;
}
/* Checked state: teal fill */
div[data-testid="stSidebar"] .stCheckbox [data-testid="stCheckbox"] input:checked + div,
div[data-testid="stSidebar"] .stCheckbox input[type="checkbox"]:checked + div {
    background-color: #518484 !important; border-color: #518484 !important;
}
/* Unchecked state: teal border so it looks cohesive */
div[data-testid="stSidebar"] .stCheckbox [data-testid="stCheckbox"] > div:first-child,
div[data-testid="stSidebar"] .stCheckbox div[role="checkbox"] {
    border-color: #518484 !important;
}
/* Hover: slightly deeper teal */
div[data-testid="stSidebar"] .stCheckbox:hover div[role="checkbox"],
div[data-testid="stSidebar"] .stCheckbox:hover [data-testid="stCheckbox"] > div:first-child {
    border-color: #3d6868 !important;
}
</style>
"""


def run_button_css(btn_bg, btn_color, btn_border, btn_hover_bg, btn_hover_color):
    return f"""
    <style>
    div[data-testid="stSidebar"] .stButton > button {{
        background: {btn_bg} !important; color: {btn_color} !important;
        border: 1px solid {btn_border} !important; border-radius: 4px !important;
        font-family: 'Century Gothic', sans-serif !important;
        font-weight: 700 !important; font-size: 0.82rem !important;
        letter-spacing: 0.06em; width: 100%;
        transition: all 0.15s ease;
    }}
    div[data-testid="stSidebar"] .stButton > button:hover {{
        background: {btn_hover_bg} !important; color: {btn_hover_color} !important;
    }}
    </style>
    """
