import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_cyrillic_font():
    """Реєстрація шрифту з підтримкою української мови"""
    font_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\arial.TTF",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "arial.ttf"
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("CyrillicFont", font_path))
                return "CyrillicFont"
            except Exception:
                pass
    return "Helvetica"


def generate_pdf_receipt(order_id: int, client_name: str, phone: str, order_date: str, 
                         status: str, total_amount: float, items: list) -> str:
    """
    Генерація та постійне збереження PDF-чека у папку receipts/
    Повертає відносний шлях до створиного файлу.
    """
    receipts_dir = "receipts"
    os.makedirs(receipts_dir, exist_ok=True)
    
    file_path = os.path.join(receipts_dir, f"receipt_{order_id}.pdf")
    font_name = register_cyrillic_font()

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=20,
        alignment=1,
        spaceAfter=10,
        textColor=colors.HexColor('#1A365D')
    )

    header_style = ParagraphStyle(
        'ReceiptHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=1,
        spaceAfter=15,
        textColor=colors.HexColor('#4A5568')
    )

    normal_style = ParagraphStyle(
        'ReceiptNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=12,
        textColor=colors.white
    )

    story = []

    story.append(Paragraph("<b>Магазин комп’ютерної техніки</b>", title_style))
    story.append(Paragraph("Товарний чек замовлення", header_style))
    story.append(Spacer(1, 10))

    info_data = [
        [
            Paragraph(f"<b>Номер замовлення:</b> №{order_id}", normal_style),
            Paragraph(f"<b>Дата та час:</b> {order_date}", normal_style)
        ],
        [
            Paragraph(f"<b>Клієнт:</b> {client_name}", normal_style),
            Paragraph(f"<b>Телефон:</b> {phone}", normal_style)
        ],
        [
            Paragraph(f"<b>Статус замовлення:</b> {status}", normal_style),
            Paragraph("<b>Оплата:</b> Готівка / Карта при отриманні", normal_style)
        ]
    ]

    info_table = Table(info_data, colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    table_data = [
        [
            Paragraph("<b>№</b>", table_header_style),
            Paragraph("<b>Товар</b>", table_header_style),
            Paragraph("<b>К-сть</b>", table_header_style),
            Paragraph("<b>Ціна (грн)</b>", table_header_style),
            Paragraph("<b>Сума (грн)</b>", table_header_style)
        ]
    ]

    for idx, item in enumerate(items, 1):
        title = item.get('title', 'Товар')
        qty = item.get('quantity', 1)
        price = item.get('price_per_unit', 0.0)
        item_total = qty * price

        table_data.append([
            Paragraph(str(idx), normal_style),
            Paragraph(title, normal_style),
            Paragraph(str(qty), normal_style),
            Paragraph(f"{price:.2f}", normal_style),
            Paragraph(f"{item_total:.2f}", normal_style)
        ])

    items_table = Table(table_data, colWidths=[30, 240, 50, 100, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EDF2F7')])
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    total_data = [
        [
            Paragraph("<b>ЗАГАЛЬНА СУМА:</b>", ParagraphStyle('TotalText', parent=normal_style, fontSize=12)),
            Paragraph(f"<b>{total_amount:.2f} грн</b>", ParagraphStyle('TotalSum', parent=normal_style, fontSize=14, textColor=colors.HexColor('#C53030')))
        ]
    ]
    total_table = Table(total_data, colWidths=[350, 170])
    total_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 20))

    footer_style = ParagraphStyle(
        'ReceiptFooter',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=1,
        textColor=colors.HexColor('#718096')
    )
    story.append(Paragraph("Дякуємо за покупку в «Магазині комп’ютерної техніки»!", footer_style))

    doc.build(story)
    return file_path
