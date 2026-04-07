"""
38DN Pricing Model Review — PDF Export
Generates a branded single-page PDF summary for quick email sharing.
Uses reportlab with built-in Helvetica (Century Gothic not available in reportlab).
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect

from utils import safe_float
from validation import validate_project
from config import BIBLE_BENCHMARKS

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------
NAVY = HexColor("#050D25")
NAVY2 = HexColor("#212B48")
TEAL = HexColor("#518484")
RED = HexColor("#b83230")
LIGHT_GREY = HexColor("#E2E7F1")
WHITE = HexColor("#FFFFFF")
TEXT_DARK = HexColor("#282828")

# ---------------------------------------------------------------------------
# Key metric rows (row_number, label, unit, is_pct)
# ---------------------------------------------------------------------------
KEY_METRICS = [
    (38,  "NPP",             "$/W",   False),
    (33,  "FMV Calculated",  "$/W",   False),
    (129, "Total CapEx",     "$/W",   False),
    (118, "EPC Cost",        "$/W",   False),
    (157, "PPA Rate",        "$/kWh", False),
    (597, "ITC Rate",        "%",     True),
    (11,  "System Size",     "MWdc",  False),
]


def _fmt_val(val, is_pct):
    """Format a numeric value for display."""
    if val is None:
        return "\u2014"
    if is_pct:
        if abs(val) < 1:
            return f"{val:.1%}"
        return f"{val:.1f}%"
    if abs(val) > 100:
        return f"{val:,.1f}"
    return f"{val:.4f}"


def _fmt_delta(delta, is_pct):
    """Format a delta value."""
    if delta is None:
        return "\u2014"
    if is_pct:
        if abs(delta) < 1:
            return f"{delta:+.2%}"
        return f"{delta:+.2f}%"
    if abs(delta) > 100:
        return f"{delta:+,.1f}"
    return f"{delta:+.4f}"


def generate_pdf(
    proj_name,
    proj1_data,
    proj2_data=None,
    m1_label="Model 1",
    m2_label="Model 2",
):
    """
    Generate a single-page branded PDF summary.

    Parameters
    ----------
    proj_name : str
        Project name(s) for the header.
    proj1_data : dict
        Row-keyed data from Model 1.
    proj2_data : dict or None
        Row-keyed data from Model 2 (for comparison).
    m1_label, m2_label : str
        Labels for the two models.

    Returns
    -------
    io.BytesIO
        PDF file buffer, ready for Streamlit download_button.
    """
    buf = io.BytesIO()
    has_comparison = proj2_data is not None and bool(proj2_data)

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    style_title = ParagraphStyle(
        "PDFTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=white,
        spaceAfter=0,
        spaceBefore=0,
        alignment=TA_LEFT,
    )
    style_subtitle = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=HexColor("#CCCCCC"),
        spaceAfter=0,
        spaceBefore=2,
        alignment=TA_LEFT,
    )
    style_section = ParagraphStyle(
        "PDFSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "PDFBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=TEXT_DARK,
        leading=11,
    )
    style_footer = ParagraphStyle(
        "PDFFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=HexColor("#888888"),
        alignment=TA_CENTER,
    )

    elements = []

    # ------------------------------------------------------------------
    # Header: navy gradient bar
    # ------------------------------------------------------------------
    header_h = 58
    d = Drawing(doc.width, header_h)
    d.add(Rect(0, 0, doc.width, header_h, fillColor=NAVY, strokeColor=None))
    # Teal accent line at bottom of bar
    d.add(Rect(0, 0, doc.width, 3, fillColor=TEAL, strokeColor=None))
    elements.append(d)

    # Title and date inside a table overlaid on the bar
    header_data = [
        [
            Paragraph("38 Degrees North  |  Pricing Model Review", style_title),
        ],
        [
            Paragraph(
                f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
                style_subtitle,
            ),
        ],
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 4),
        ("BOTTOMPADDING", (-1, -1), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))

    # ------------------------------------------------------------------
    # Project info
    # ------------------------------------------------------------------
    proj_name_1 = str(proj1_data.get(4, proj_name)) if proj1_data else proj_name
    proj_name_2 = str(proj2_data.get(4, "")) if has_comparison and proj2_data else ""
    state = str(proj1_data.get(18, "")) if proj1_data else ""

    info_parts = [f"<b>Project:</b> {proj_name_1}"]
    if proj_name_2 and proj_name_2 != proj_name_1:
        info_parts.append(f"<b>Comparison:</b> {proj_name_2}")
    if state:
        info_parts.append(f"<b>State:</b> {state}")
    info_parts.append(f"<b>Models:</b> {m1_label}")
    if has_comparison:
        info_parts[-1] += f" vs {m2_label}"

    elements.append(Paragraph("  |  ".join(info_parts), style_body))
    elements.append(Spacer(1, 6))

    # ------------------------------------------------------------------
    # Key Metrics table
    # ------------------------------------------------------------------
    elements.append(Paragraph("Key Metrics", style_section))

    if has_comparison:
        col_headers = ["Metric", "Unit", m1_label, m2_label, "Delta"]
        col_widths = [1.8 * inch, 0.7 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch]
    else:
        col_headers = ["Metric", "Unit", m1_label]
        col_widths = [2.2 * inch, 0.8 * inch, 2.0 * inch]

    table_data = [col_headers]

    for row_num, label, unit, is_pct in KEY_METRICS:
        v1 = safe_float(proj1_data.get(row_num)) if proj1_data else None
        v2 = safe_float(proj2_data.get(row_num)) if has_comparison and proj2_data else None

        row = [label, unit, _fmt_val(v1, is_pct)]
        if has_comparison:
            row.append(_fmt_val(v2, is_pct))
            delta = (v2 - v1) if v1 is not None and v2 is not None else None
            row.append(_fmt_delta(delta, is_pct))
        table_data.append(row)

    metrics_table = Table(table_data, colWidths=col_widths, hAlign="LEFT")

    # Style
    ts = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Body rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_DARK),
        # Alternating row backgrounds
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        # Right-align numeric columns
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (1, -1), "LEFT"),
    ]

    # Alternating row shading
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GREY))

    # Color negative deltas red (in the Delta column, which is the last column)
    if has_comparison:
        delta_col = len(col_headers) - 1
        for i in range(1, len(table_data)):
            row_num_metric = KEY_METRICS[i - 1][0]
            v1 = safe_float(proj1_data.get(row_num_metric)) if proj1_data else None
            v2 = safe_float(proj2_data.get(row_num_metric)) if has_comparison and proj2_data else None
            if v1 is not None and v2 is not None:
                delta = v2 - v1
                # For NPP and FMV, negative delta is bad; for costs, positive is bad
                # Simplification: flag any nonzero delta in red if negative for value metrics
                # or positive for cost metrics
                is_negative_delta = False
                if row_num_metric in (38, 33):  # NPP, FMV — lower is worse
                    is_negative_delta = delta < 0
                elif row_num_metric in (129, 118):  # costs — higher is worse
                    is_negative_delta = delta > 0
                elif row_num_metric == 157:  # PPA rate — lower is worse
                    is_negative_delta = delta < 0
                elif row_num_metric == 597:  # ITC — lower is worse
                    is_negative_delta = delta < 0
                elif row_num_metric == 11:  # system size — lower could be neutral
                    is_negative_delta = False

                if is_negative_delta:
                    ts.append(("TEXTCOLOR", (delta_col, i), (delta_col, i), RED))

    metrics_table.setStyle(TableStyle(ts))
    elements.append(metrics_table)
    elements.append(Spacer(1, 10))

    # ------------------------------------------------------------------
    # Validation summary
    # ------------------------------------------------------------------
    elements.append(Paragraph("Validation Summary", style_section))

    findings, _ = validate_project(proj1_data or {}, BIBLE_BENCHMARKS)
    total_checks = len(findings)
    n_pass = sum(1 for f in findings if f["Status"] == "OK")
    n_flags = sum(1 for f in findings if f["Status"] in ("LOW", "HIGH"))
    n_warn = sum(1 for f in findings if f["Status"] == "WARNING")

    summary_text = (
        f"<b>{n_pass}/{total_checks}</b> checks passed  |  "
        f"<b>{n_flags}</b> flag(s)  |  "
        f"<b>{n_warn}</b> missing/warning"
    )
    elements.append(Paragraph(summary_text, style_body))
    elements.append(Spacer(1, 4))

    # Flags detail table (only show issues)
    issues = [f for f in findings if f["Status"] != "OK"]
    if issues:
        flag_headers = ["Check", "Row", "Value", "Range", "Status"]
        flag_data = [flag_headers]
        for f in issues:
            val_str = _fmt_val(f["Value"], False) if f["Value"] is not None else "blank"
            range_str = f"{f['Min']} \u2013 {f['Max']}"
            flag_data.append([
                f["Check"], str(f["Row"]), val_str, range_str, f["Status"],
            ])

        flag_widths = [2.0 * inch, 0.6 * inch, 1.0 * inch, 1.2 * inch, 0.8 * inch]
        flag_table = Table(flag_data, colWidths=flag_widths, hAlign="LEFT")

        fts = [
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_DARK),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        # Color the Status column for flags
        for i in range(1, len(flag_data)):
            status = flag_data[i][-1]
            if status in ("LOW", "HIGH"):
                fts.append(("TEXTCOLOR", (-1, i), (-1, i), RED))

        flag_table.setStyle(TableStyle(fts))
        elements.append(flag_table)
    else:
        elements.append(Paragraph(
            "All checks within expected ranges.", style_body
        ))

    elements.append(Spacer(1, 12))

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    elements.append(Paragraph(
        "38 Degrees North  |  Confidential  |  Generated by VP Review App",
        style_footer,
    ))

    # ------------------------------------------------------------------
    # Build PDF
    # ------------------------------------------------------------------
    doc.build(elements)
    buf.seek(0)
    return buf
