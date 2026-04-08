from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import date
from database import MARKET_ITEMS, LOCAL_ITEMS, SHOPS

# Teal color matching your existing sheet
TEAL = colors.HexColor('#008080')
LIGHT_GRAY = colors.HexColor('#f5f5f5')

def generate_restock_pdf(orders):
    """
    Generate a PDF restock order sheet — local items on left, market items on right.
    Matches your existing segregation sheet layout.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=1*cm, rightMargin=1*cm,
                             topMargin=1.5*cm, bottomMargin=1*cm)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('title', fontSize=14, fontName='Helvetica-Bold',
                                  spaceAfter=6, alignment=1)
    date_style = ParagraphStyle('date', fontSize=9, fontName='Helvetica',
                                 spaceAfter=10, alignment=1, textColor=colors.gray)

    elements.append(Paragraph("🌿 Paan Shop — Restock Order", title_style))
    elements.append(Paragraph(f"Generated: {date.today().strftime('%d %B %Y')}", date_style))

    # Organize orders by shop
    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    # Separate local vs market per shop
    local_by_shop = {}
    market_by_shop = {}
    for shop in SHOPS:
        if shop not in orders_by_shop:
            continue
        shop_orders = orders_by_shop[shop]
        local = [(o['item_name'], o['quantity']) for o in shop_orders if o['item_name'] not in MARKET_ITEMS]
        market = [(o['item_name'], o['quantity']) for o in shop_orders if o['item_name'] in MARKET_ITEMS]
        if local:
            local_by_shop[shop] = local
        if market:
            market_by_shop[shop] = market

    # Build two-column table: LOCAL | MARKET
    col_width = (A4[0] - 2*cm) / 2 - 0.3*cm
    header_style = ParagraphStyle('hdr', fontSize=11, fontName='Helvetica-Bold',
                                   textColor=colors.white)
    shop_style = ParagraphStyle('shop', fontSize=9, fontName='Helvetica-Bold',
                                 textColor=colors.white)
    item_style = ParagraphStyle('item', fontSize=8, fontName='Helvetica',
                                 textColor=colors.black)
    total_style = ParagraphStyle('total', fontSize=8, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#333333'))

    def build_shop_block(shop, items, is_market=False):
        block = []
        # Shop header row
        block.append([Paragraph(shop, shop_style), ''])
        for item_name, qty in items:
            price = MARKET_ITEMS.get(item_name, 0) if is_market else 0
            cost_str = f"₹{price * qty:,.0f}" if price else ""
            block.append([
                Paragraph(f"  {item_name} - {int(qty) if qty == int(qty) else qty}", item_style),
                Paragraph(cost_str, item_style)
            ])
        if is_market:
            total_cost = sum(MARKET_ITEMS.get(i, 0) * q for i, q in items)
            block.append([Paragraph(f"  कुल / Total: ₹{total_cost:,.0f}", total_style), ''])
        return block

    all_shops = sorted(set(list(local_by_shop.keys()) + list(market_by_shop.keys())))

    # Section headers
    sec_header_data = [
        [Paragraph("🟢 LOCAL ITEMS / लोकल आइटम", header_style),
         Paragraph("🔵 MARKET ITEMS / मार्केट आइटम", header_style)]
    ]
    sec_header_table = Table(sec_header_data, colWidths=[col_width, col_width])
    sec_header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), TEAL),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#1565c0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(sec_header_table)
    elements.append(Spacer(1, 4))

    # Per shop rows
    for shop in all_shops:
        local_items = local_by_shop.get(shop, [])
        market_items = market_by_shop.get(shop, [])

        local_block = build_shop_block(shop, local_items, False) if local_items else []
        market_block = build_shop_block(shop, market_items, True) if market_items else []

        max_rows = max(len(local_block), len(market_block))
        # Pad shorter side
        while len(local_block) < max_rows:
            local_block.append([Paragraph("", item_style), ''])
        while len(market_block) < max_rows:
            market_block.append([Paragraph("", item_style), ''])

        combined_data = []
        for i in range(max_rows):
            combined_data.append([
                local_block[i][0], local_block[i][1] if len(local_block[i]) > 1 else '',
                market_block[i][0], market_block[i][1] if len(market_block[i]) > 1 else ''
            ])

        table = Table(combined_data,
                      colWidths=[col_width * 0.75, col_width * 0.25,
                                  col_width * 0.75, col_width * 0.25])

        style = TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.lightgrey),
            ('LINEAFTER', (1, 0), (1, -1), 0.5, colors.lightgrey),
        ])

        # Header rows (shop name) — teal background
        for i, row in enumerate(combined_data):
            left_text = row[0].text if hasattr(row[0], 'text') else ''
            right_text = row[2].text if hasattr(row[2], 'text') else ''
            if shop in (left_text or '') and i == 0:
                style.add('BACKGROUND', (0, i), (1, i), TEAL)
            if shop in (right_text or '') and i == 0:
                style.add('BACKGROUND', (2, i), (3, i), colors.HexColor('#1565c0'))

        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 3))

    # Market cost summary
    elements.append(Spacer(1, 10))
    summary_style = ParagraphStyle('summary', fontSize=10, fontName='Helvetica-Bold',
                                    spaceAfter=4)
    elements.append(Paragraph("Market Cost Summary / मार्केट लागत सारांश", summary_style))

    summary_data = [["Shop / दुकान", "Items", "Total Cost ₹"]]
    grand_total = 0
    for shop, items in market_by_shop.items():
        cost = sum(MARKET_ITEMS.get(i, 0) * q for i, q in items)
        grand_total += cost
        summary_data.append([shop, len(items), f"₹{cost:,.0f}"])
    summary_data.append(["TOTAL / कुल", "", f"₹{grand_total:,.0f}"])

    summary_table = Table(summary_data, colWidths=[6*cm, 3*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT_GRAY]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
