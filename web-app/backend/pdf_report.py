"""
LeafScan — PDF Diagnosis Report Generator
=========================================
Generates professional agricultural advisory PDF reports using ReportLab.
Includes LeafScan branding, scan metadata, leaf photograph, diagnosis,
confidence score, and actionable agronomic treatment recommendations.
"""

import io
import os
from datetime import datetime
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_pdf_report(scan: Dict[str, Any], uploads_dir: str) -> io.BytesIO:
    """Generate a PDF report for a given scan dictionary and return an in-memory BytesIO buffer."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles matching LeafScan brand palette (#0b8379, #0a2a2a, #166b42)
    primary_color = colors.HexColor("#0B8379")
    dark_color = colors.HexColor("#0A2A2A")
    muted_color = colors.HexColor("#55706F")
    border_color = colors.HexColor("#D3E4E2")
    bg_light = colors.HexColor("#F3FAF9")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=muted_color,
        spaceAfter=10,
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=dark_color,
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=dark_color,
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=dark_color,
    )
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_color,
        leftIndent=12,
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=muted_color,
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>LEAFSCAN</b> &mdash; AI Tomato Health Platform", title_style),
            Paragraph(f"<b>Report ID:</b> #{scan.get('id', 'N/A')}<br/><b>Date:</b> {scan.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M'))}", ParagraphStyle('RightMeta', parent=subtitle_style, alignment=2)),
        ]
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=12))

    # 2. Scan & Farm Overview Metadata
    farm_name = scan.get('farm_name') or 'General / Unassigned Farm'
    pred_label = scan.get('prediction_label', 'Unknown')
    is_healthy = bool(scan.get('is_healthy', 0))
    conf = scan.get('confidence', 0.0)

    # Color badge for status
    if is_healthy:
        status_bg = colors.HexColor("#DCFCE7")
        status_fg = "#166534"
    elif 'late' in pred_label.lower():
        status_bg = colors.HexColor("#FEE2E2")
        status_fg = "#991B1B"
    else:
        status_bg = colors.HexColor("#FEF3C7")
        status_fg = "#92400E"

    overview_rows = [
        [
            Paragraph("<b>Farm Plot:</b>", body_style),
            Paragraph(str(farm_name), body_style),
            Paragraph("<b>Diagnosis:</b>", body_style),
            Paragraph(f"<font color='{status_fg}'><b>{pred_label}</b></font>", body_style),
        ],
        [
            Paragraph("<b>Model Confidence:</b>", body_style),
            Paragraph(f"<b>{conf:.1f}%</b>", body_style),
            Paragraph("<b>Classification Type:</b>", body_style),
            Paragraph(str(scan.get('disease_type') or ('Healthy' if is_healthy else 'Fungal')), body_style),
        ],
        [
            Paragraph("<b>Inspection Date:</b>", body_style),
            Paragraph(str(scan.get('created_at', 'N/A')), body_style),
            Paragraph("<b>Platform Source:</b>", body_style),
            Paragraph(f"{scan.get('platform', 'Web').capitalize()} ({scan.get('model_name', 'Default Model')})", body_style),
        ],
    ]
    overview_table = Table(overview_rows, colWidths=[1.5 * inch, 2.1 * inch, 1.5 * inch, 2.1 * inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 12))

    # 3. Image and Summary Layout
    raw_data = scan.get('raw_json') or {}
    disease_info = raw_data.get('disease') or {}

    image_filename = scan.get('image_filename', '')
    image_path = os.path.join(uploads_dir, image_filename) if image_filename else None

    img_flowable = None
    if image_path and os.path.isfile(image_path):
        try:
            img_flowable = RLImage(image_path, width=2.4 * inch, height=2.4 * inch)
        except Exception:
            img_flowable = Paragraph("<i>[Leaf Image Attached in Record]</i>", body_style)
    else:
        img_flowable = Paragraph("<i>[Leaf Photo Archive]</i>", body_style)

    summary_text = scan.get('disease_summary') or disease_info.get('summary') or 'Even green leaf with no symptoms detected.'
    cause_text = scan.get('disease_cause') or disease_info.get('cause') or 'None detected.'

    summary_paras = [
        Paragraph("<b>Clinical Pathology & Summary</b>", section_heading),
        Paragraph(summary_text, body_style),
        Spacer(1, 6),
        Paragraph("<b>Underlying Cause / Etiology:</b>", bold_style),
        Paragraph(cause_text, body_style),
    ]

    media_table = Table([[img_flowable, summary_paras]], colWidths=[2.6 * inch, 4.6 * inch])
    media_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (1, 0), (1, 0), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(media_table)
    story.append(Spacer(1, 10))

    # 4. Actionable Treatment Guidance (3 Column / Block Section)
    stop_now = disease_info.get('stopNow') or ['Regular scouting and preventative care.']
    prevent_spread = disease_info.get('preventSpread') or ['Disinfect tools and wash hands between plant blocks.']
    treatments = disease_info.get('treatments') or ['No chemical treatments required for healthy foliage.']
    prevent_future = disease_info.get('preventFuture') or ['Maintain optimal plant spacing and drip irrigation at plant base.']

    story.append(Paragraph("<b>Agronomic Management & Containment Directives</b>", section_heading))

    advice_data = [
        [
            Paragraph("<b>Immediate Intervention</b>", bold_style),
            Paragraph("<b>Spread Control Measures</b>", bold_style),
        ],
        [
            [Paragraph(f"&bull; {item}", bullet_style) for item in stop_now],
            [Paragraph(f"&bull; {item}", bullet_style) for item in prevent_spread],
        ],
        [
            Paragraph("<b>Recommended Treatments</b>", bold_style),
            Paragraph("<b>Long-Term Prevention</b>", bold_style),
        ],
        [
            [Paragraph(f"&bull; {item}", bullet_style) for item in treatments],
            [Paragraph(f"&bull; {item}", bullet_style) for item in prevent_future],
        ],
    ]

    advice_table = Table(advice_data, colWidths=[3.5 * inch, 3.7 * inch])
    advice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), bg_light),
        ('BACKGROUND', (0, 2), (-1, 2), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(advice_table)
    story.append(Spacer(1, 14))

    # 5. Mandatory Advisory Disclaimer
    disclaimer_text = (
        "<b>ADVISORY DISCLAIMER:</b> This report is generated by an AI-assisted tomato leaf disease "
        "detection system. Results are informational and should not replace professional agricultural diagnosis. "
        "Always cross-reference with in-field physical inspections and local agricultural extension officers "
        "before applying regulated agrochemical treatments."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[7.2 * inch])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([disclaimer_table]))

    doc.build(story)
    buf.seek(0)
    return buf
