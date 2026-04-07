"""
38DN Pricing Model Review — Excel Export
Generates branded XLSX with Variance and Full comparison sheets.
Style mirrors 38DN walk/pricing summary formatting (Aptos Narrow, navy headers, etc.)
"""

import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Style constants (from 38DN walk files)
# ---------------------------------------------------------------------------

# Fonts
FONT_LABEL = Font(name="Aptos Narrow", size=11, color="050D25")
FONT_LABEL_BOLD = Font(name="Aptos Narrow", size=11, bold=True, color="050D25")
FONT_HEADER = Font(name="Aptos Display", size=11, bold=True, color="FFFFFF")
FONT_HEADER_REG = Font(name="Aptos Display", size=11, color="FFFFFF")
FONT_UNIT = Font(name="Aptos Narrow", size=11, italic=True, color="0000FF")
FONT_SECTION = Font(name="Aptos Narrow", size=11, bold=True, color="050D25")
FONT_DATA = Font(name="Aptos Narrow", size=11, color="050D25")
FONT_DATA_BOLD = Font(name="Aptos Narrow", size=11, bold=True, color="050D25")
FONT_NEG = Font(name="Aptos Narrow", size=11, color="B83230")
FONT_NEG_BOLD = Font(name="Aptos Narrow", size=11, bold=True, color="B83230")

# Fills
FILL_NAVY = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
FILL_NAVY2 = PatternFill(start_color="212B48", end_color="212B48", fill_type="solid")
FILL_LIGHT_GRAY = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
FILL_GRAY = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
FILL_ICE_BLUE = PatternFill(start_color="DDEFF7", end_color="DDEFF7", fill_type="solid")
FILL_LAVENDER = PatternFill(start_color="C7CFE6", end_color="C7CFE6", fill_type="solid")
FILL_NONE = PatternFill(fill_type=None)

# Borders
THIN = Side(style="thin")
DOUBLE = Side(style="double")
HAIR = Side(style="hair")
BORDER_STD = Border(top=THIN, bottom=THIN)
BORDER_SECTION = Border(bottom=DOUBLE)
BORDER_HEADER = Border(top=THIN, bottom=THIN, right=THIN)
BORDER_NONE = Border()

# Alignment
ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

# Number formats
NF_PCT = "0.00%"
NF_PCT1 = "0.0%"
NF_DPW3 = '0.000_);\\(0.000\\)'  # $/W with parens for neg
NF_DPW3_RED = '0.000_);[Red]\\(0.000\\)'  # red neg
NF_DPW2 = "0.00"
NF_INT = "#,##0"
NF_DOLLAR = '"$"#,##0'
NF_YEAR = "0"
NF_GENERAL = "General"

# Rows that are percentages
PCT_ROWS = {30, 31, 36, 37, 158, 161, 162, 168, 219, 220, 221, 227, 229, 231,
            237, 241, 282, 283, 286, 288, 293, 297, 299, 597, 602}
TEXT_ROWS = {4, 8, 10, 18, 19, 21, 22, 117, 155, 156,
             165, 166, 591, 596}
DATE_ROWS = {68, 69, 70, 71, 72, 73}
# Rows in $/W (3 decimal)
DPW_ROWS = {32, 33, 38, 118, 119, 120, 121, 122, 123, 124, 126, 129, 157, 167, 216, 218}
# Rows that are integers / large numbers
INT_ROWS = {15, 16, 17, 24, 25, 143, 160, 170, 217, 225, 226, 228, 230, 235,
            240, 256, 258, 284, 285, 292, 296, 298, 302}
# Output rows (highlight)
OUTPUT_HIGHLIGHT = {38, 39, 33}


def safe_float(v):
    if v is None: return None
    try: return float(v)
    except (ValueError, TypeError): return None


NF_DATE = "MM/DD/YYYY"

def get_nf(row):
    """Get the appropriate number format for a row."""
    if row in PCT_ROWS: return NF_PCT
    if row in DPW_ROWS: return NF_DPW3_RED
    if row in INT_ROWS: return NF_INT
    if row in TEXT_ROWS: return NF_GENERAL
    if row in DATE_ROWS: return NF_DATE
    return NF_DPW2


def write_comparison_sheet(ws, comp_rows, label1, label2, title, variance_only=False):
    """Write a formatted comparison table to a worksheet.

    Args:
        ws: openpyxl worksheet
        comp_rows: list of dicts with Row, Field, label1, label2, Delta, Delta %, _delta_raw, _pct_raw
        label1, label2: column header labels
        title: sheet title text
        variance_only: if True, only include rows where values differ
    """
    # Filter if variance only
    if variance_only:
        comp_rows = [r for r in comp_rows if r.get("_delta_raw") is not None and r["_delta_raw"] != 0
                     or r.get(label1) != r.get(label2)]

    # Column widths
    ws.column_dimensions["A"].width = 3.0   # spacer
    ws.column_dimensions["B"].width = 8.0   # Row #
    ws.column_dimensions["C"].width = 35.0  # Field
    ws.column_dimensions["D"].width = 8.0   # Units
    ws.column_dimensions["E"].width = 16.0  # Model 1
    ws.column_dimensions["F"].width = 16.0  # Model 2
    ws.column_dimensions["G"].width = 16.0  # Delta
    ws.column_dimensions["H"].width = 14.0  # Delta %

    # Row 2: Title
    ws.merge_cells("B2:H2")
    c = ws["B2"]
    c.value = title
    c.font = FONT_LABEL_BOLD
    c.alignment = ALIGN_LEFT

    # Row 4: Header banner
    headers = ["Row", "Field", "Units", label1, label2, "Delta (units)", "Delta (%)"]
    cols = ["B", "C", "D", "E", "F", "G", "H"]
    for i, (col, hdr) in enumerate(zip(cols, headers)):
        cell = ws[f"{col}4"]
        cell.value = hdr
        cell.font = FONT_HEADER if i < 3 else FONT_HEADER
        cell.fill = FILL_NAVY
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_HEADER

    # Row 5: Units sub-header
    ws["D5"].font = FONT_UNIT
    ws["D5"].alignment = ALIGN_CENTER

    # Data rows starting at row 6
    current_row = 6
    prev_section = None

    for rd in comp_rows:
        row_num = rd.get("Row", "")
        field = rd.get("Field", "")
        is_output = row_num in OUTPUT_HIGHLIGHT
        is_text = row_num in TEXT_ROWS or row_num in DATE_ROWS
        is_pct = row_num in PCT_ROWS

        # Detect section breaks (rows with no data = section headers)
        # Insert section separator for key sections
        section_breaks = {
            4: "Project Details", 68: "Milestones",
            118: "CapEx", 143: "Revenue",
            147: "Rate Component 1", 148: "Rate Component 2",
            216: "Incentives", 225: "OpEx", 282: "Decommissioning",
            291: "Property Tax & Insurance", 587: "Tax & Depreciation",
            32: "Outputs",
        }
        if row_num in section_breaks and section_breaks[row_num] != prev_section:
            prev_section = section_breaks[row_num]
            ws[f"B{current_row}"].border = BORDER_SECTION
            ws[f"C{current_row}"].value = prev_section
            ws[f"C{current_row}"].font = FONT_SECTION
            ws[f"C{current_row}"].border = BORDER_SECTION
            for col in ["D", "E", "F", "G", "H"]:
                ws[f"{col}{current_row}"].border = BORDER_SECTION
            current_row += 1

        # Row number
        ws[f"B{current_row}"].value = row_num
        ws[f"B{current_row}"].font = FONT_DATA
        ws[f"B{current_row}"].alignment = ALIGN_CENTER
        ws[f"B{current_row}"].border = BORDER_STD

        # Field name
        ws[f"C{current_row}"].value = field
        ws[f"C{current_row}"].font = FONT_DATA_BOLD if is_output else FONT_DATA
        ws[f"C{current_row}"].alignment = ALIGN_LEFT
        ws[f"C{current_row}"].border = BORDER_STD
        if is_output:
            ws[f"C{current_row}"].fill = FILL_ICE_BLUE

        # Units
        nf = get_nf(row_num)
        unit_text = ""
        if is_pct: unit_text = "%"
        elif row_num in DPW_ROWS: unit_text = "$/W"
        elif row_num in INT_ROWS: unit_text = "#"
        elif is_text: unit_text = "text"
        ws[f"D{current_row}"].value = unit_text
        ws[f"D{current_row}"].font = FONT_UNIT
        ws[f"D{current_row}"].alignment = ALIGN_CENTER
        ws[f"D{current_row}"].border = BORDER_STD

        # Model 1 value
        v1_str = rd.get(label1, "")
        v1_raw = rd.get("_v1_raw")
        cell_e = ws[f"E{current_row}"]
        if v1_raw is not None and not is_text:
            cell_e.value = v1_raw
            cell_e.number_format = nf
        else:
            cell_e.value = v1_str if v1_str != "\u2014" else ""
        cell_e.font = FONT_DATA_BOLD if is_output else FONT_DATA
        cell_e.alignment = ALIGN_CENTER
        cell_e.border = BORDER_STD
        if is_output: cell_e.fill = FILL_ICE_BLUE

        # Model 2 value
        v2_str = rd.get(label2, "")
        v2_raw = rd.get("_v2_raw")
        cell_f = ws[f"F{current_row}"]
        if v2_raw is not None and not is_text:
            cell_f.value = v2_raw
            cell_f.number_format = nf
        else:
            cell_f.value = v2_str if v2_str != "\u2014" else ""
        cell_f.font = FONT_DATA_BOLD if is_output else FONT_DATA
        cell_f.alignment = ALIGN_CENTER
        cell_f.border = BORDER_STD
        if is_output: cell_f.fill = FILL_ICE_BLUE

        # Delta
        delta = rd.get("_delta_raw")
        cell_g = ws[f"G{current_row}"]
        if delta is not None and not is_text:
            cell_g.value = delta
            cell_g.number_format = nf
            cell_g.font = FONT_NEG_BOLD if delta < 0 else (FONT_DATA_BOLD if is_output else FONT_DATA)
        else:
            cell_g.value = ""
        cell_g.alignment = ALIGN_CENTER
        cell_g.border = BORDER_STD

        # Delta %
        pct = rd.get("_pct_raw")
        cell_h = ws[f"H{current_row}"]
        if pct is not None and not is_text:
            cell_h.value = pct
            cell_h.number_format = '0.00%;[Red]\\(0.00%\\);"-"'
            cell_h.font = FONT_NEG if pct < 0 else FONT_DATA
        else:
            cell_h.value = ""
        cell_h.alignment = ALIGN_CENTER
        cell_h.border = BORDER_STD

        # Alternating row fill
        if current_row % 2 == 0 and not is_output:
            for col in ["B", "C", "D", "E", "F", "G", "H"]:
                if ws[f"{col}{current_row}"].fill == FILL_NONE or ws[f"{col}{current_row}"].fill.fgColor.rgb == "00000000":
                    ws[f"{col}{current_row}"].fill = FILL_LIGHT_GRAY

        current_row += 1

    # Freeze panes
    ws.freeze_panes = "E5"

    return current_row


def generate_comparison_xlsx(comp_data, label1, label2, title="Model Comparison"):
    """Generate a branded Excel workbook with Variance and Full sheets.

    Args:
        comp_data: list of dicts from build_comparison_table with added _v1_raw, _v2_raw keys
        label1, label2: model labels
        title: workbook title

    Returns: BytesIO buffer
    """
    wb = openpyxl.Workbook()

    # Sheet 1: Variance (only differences)
    ws_var = wb.active
    ws_var.title = "Variance"
    write_comparison_sheet(ws_var, comp_data, label1, label2,
                           f"{title} \u2014 Variance Only", variance_only=True)

    # Sheet 2: Full (all rows)
    ws_full = wb.create_sheet("Full Comparison")
    write_comparison_sheet(ws_full, comp_data, label1, label2,
                           f"{title} \u2014 Full Inputs", variance_only=False)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_export_rows(proj1_data, proj2_data, label1, label2):
    """Build comparison rows with raw values for Excel export."""
    from app import INPUT_ROW_LABELS, OUTPUT_ROWS

    all_rows = sorted(set(INPUT_ROW_LABELS.keys()) | set(OUTPUT_ROWS.keys()))
    result = []

    for r in all_rows:
        label = INPUT_ROW_LABELS.get(r, OUTPUT_ROWS.get(r, f"Row {r}"))
        v1_raw_val = proj1_data.get(r) if proj1_data else None
        v2_raw_val = proj2_data.get(r) if proj2_data else None

        is_text = r in TEXT_ROWS
        is_pct = r in PCT_ROWS

        v1 = safe_float(v1_raw_val) if not is_text else None
        v2 = safe_float(v2_raw_val) if not is_text else None

        def fv(v):
            if v is None: return "\u2014"
            if is_pct: return f"{v:.2%}" if abs(v) < 1 else f"{v:.2f}%"
            if abs(v) > 1000: return f"{v:,.0f}"
            return f"{v:.4f}"

        delta = (v2 - v1) if v1 is not None and v2 is not None else None
        pct = (delta / abs(v1)) if delta is not None and v1 and v1 != 0 else None

        result.append({
            "Row": r, "Field": label,
            label1: fv(v1) if not is_text else str(v1_raw_val or ""),
            label2: fv(v2) if not is_text else str(v2_raw_val or ""),
            "_v1_raw": v1 if not is_text else None,
            "_v2_raw": v2 if not is_text else None,
            "_delta_raw": delta,
            "_pct_raw": pct,
        })

    return result


def _truncate_sheet_name(name, suffix, max_len=31):
    """Build a sheet name from a project name + suffix, truncated to Excel's 31-char limit.
    Also replaces characters invalid in sheet names."""
    for ch in ["\\", "/", "*", "?", ":", "[", "]"]:
        name = name.replace(ch, "_")
    prefix_budget = max_len - len(suffix) - 1  # 1 for the separator
    if prefix_budget < 1:
        prefix_budget = 1
    short = name[:prefix_budget]
    result = f"{short} {suffix}"
    return result[:max_len]


# Key metric rows for the summary sheet
_SUMMARY_METRICS = [
    (38,  "NPP ($/W)"),
    (33,  "FMV Calculated ($/W)"),
    (118, "PV EPC Cost ($/W)"),
    (122, "IX Cost ($/W)"),
    (129, "Total Capex Excl. Financing"),
    (597, "ITC Rate (%)"),
    (602, "Eligible Costs (%)"),
    (11,  "System Size (MWdc)"),
    (157, "Energy Rate (at COD)"),
]


def generate_multi_project_xlsx(projects_data, label1, label2, title="Multi-Project Comparison"):
    """Generate a branded Excel workbook with a Summary sheet and per-project Variance/Full sheets.

    Args:
        projects_data: list of (project_name, data1, data2) tuples
        label1, label2: model labels
        title: workbook title

    Returns: BytesIO buffer
    """
    wb = openpyxl.Workbook()

    # ---- Sheet 1: Summary ----
    ws_sum = wb.active
    ws_sum.title = "Summary"

    ws_sum.column_dimensions["A"].width = 3.0
    ws_sum.column_dimensions["B"].width = 28.0  # Project name

    # Title row
    ws_sum.merge_cells("B2:H2")
    ws_sum["B2"].value = title
    ws_sum["B2"].font = FONT_LABEL_BOLD
    ws_sum["B2"].alignment = ALIGN_LEFT

    # Build header columns: B=Project, then for each metric: label1, label2
    headers = ["Project"]
    col_idx = 2  # start at C
    metric_col_pairs = []  # list of (col_letter_1, col_letter_2) for each metric
    for _, metric_label in _SUMMARY_METRICS:
        c1 = get_column_letter(col_idx)
        c2 = get_column_letter(col_idx + 1)
        headers.append(f"{metric_label} ({label1})")
        headers.append(f"{metric_label} ({label2})")
        metric_col_pairs.append((c1, c2))
        # Set column widths
        ws_sum.column_dimensions[c1].width = 18.0
        ws_sum.column_dimensions[c2].width = 18.0
        col_idx += 2

    # Write header row at row 4
    header_row = 4
    ws_sum[f"B{header_row}"].value = "Project"
    ws_sum[f"B{header_row}"].font = FONT_HEADER
    ws_sum[f"B{header_row}"].fill = FILL_NAVY
    ws_sum[f"B{header_row}"].alignment = ALIGN_CENTER
    ws_sum[f"B{header_row}"].border = BORDER_HEADER

    for i, (_, metric_label) in enumerate(_SUMMARY_METRICS):
        c1, c2 = metric_col_pairs[i]
        for col_letter, lbl in [(c1, label1), (c2, label2)]:
            cell = ws_sum[f"{col_letter}{header_row}"]
            cell.value = f"{metric_label}\n({lbl})"
            cell.font = FONT_HEADER
            cell.fill = FILL_NAVY
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER_HEADER

    # Data rows
    data_row = 5
    for proj_name, d1, d2 in projects_data:
        ws_sum[f"B{data_row}"].value = proj_name
        ws_sum[f"B{data_row}"].font = FONT_DATA_BOLD
        ws_sum[f"B{data_row}"].alignment = ALIGN_LEFT
        ws_sum[f"B{data_row}"].border = BORDER_STD

        for i, (row_num, _) in enumerate(_SUMMARY_METRICS):
            c1, c2 = metric_col_pairs[i]
            nf = get_nf(row_num)
            v1 = safe_float(d1.get(row_num)) if d1 else None
            v2 = safe_float(d2.get(row_num)) if d2 else None

            cell1 = ws_sum[f"{c1}{data_row}"]
            cell2 = ws_sum[f"{c2}{data_row}"]
            for cell, val in [(cell1, v1), (cell2, v2)]:
                if val is not None:
                    cell.value = val
                    cell.number_format = nf
                else:
                    cell.value = ""
                cell.font = FONT_DATA
                cell.alignment = ALIGN_CENTER
                cell.border = BORDER_STD

        # Alternating row fill
        if data_row % 2 == 0:
            last_col = get_column_letter(1 + len(_SUMMARY_METRICS) * 2)
            for ci in range(2, 2 + len(_SUMMARY_METRICS) * 2 + 1):
                cl = get_column_letter(ci)
                c = ws_sum[f"{cl}{data_row}"]
                if c.fill == FILL_NONE or c.fill.fgColor.rgb == "00000000":
                    c.fill = FILL_LIGHT_GRAY

        data_row += 1

    ws_sum.freeze_panes = "C5"

    # ---- Per-project sheets ----
    for proj_name, d1, d2 in projects_data:
        export_rows = build_export_rows(d1, d2, label1, label2)
        proj_title = f"{proj_name} \u2014 {label1} vs {label2}"

        # Variance sheet
        var_name = _truncate_sheet_name(proj_name, "Var")
        ws_var = wb.create_sheet(var_name)
        write_comparison_sheet(ws_var, export_rows, label1, label2,
                               f"{proj_title} \u2014 Variance Only", variance_only=True)

        # Full sheet
        full_name = _truncate_sheet_name(proj_name, "Full")
        ws_full = wb.create_sheet(full_name)
        write_comparison_sheet(ws_full, export_rows, label1, label2,
                               f"{proj_title} \u2014 Full Inputs", variance_only=False)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
