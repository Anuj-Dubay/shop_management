from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import date
from database import MARKET_ITEMS, LOCAL_ITEMS, SHOPS

try:
    pdfmetrics.registerFont(TTFont('Hindi', '/usr/share/fonts/truetype/freefont/FreeSans.ttf'))
    pdfmetrics.registerFont(TTFont('HindiBold', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'))
    FONT = 'Hindi'
    FONT_BOLD = 'HindiBold'
except:
    FONT = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

TEAL = colors.HexColor('#008080')
BLUE = colors.HexColor('#1565c0')
LIGHT_GRAY = colors.HexColor('#f5f5f5')

KEEP_ITEMS = ['tin', 'katha', 'टिन', 'कथा']

def classify_item(item_name):
    if item_name in KEEP_ITEMS:
        return 'keep'
    if item_name in MARKET_ITEMS:
        return 'market'
    return 'local'

def generate_restock_pdf(orders, show_costs=True):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=0.8*cm, rightMargin=0.8*cm,
                             topMargin=1.2*cm, bottomMargin=0.8*cm)
    elements = []

    title_s = ParagraphStyle('t', fontName=FONT_BOLD, fontSize=13, spaceAfter=4, alignment=1)
    date_s  = ParagraphStyle('d', fontName=FONT, fontSize=8, spaceAfter=8, alignment=1, textColor=colors.gray)
    shop_s  = ParagraphStyle('sh', fontName=FONT_BOLD, fontSize=9, textColor=colors.white)
    item_s  = ParagraphStyle('i', fontName=FONT, fontSize=8, textColor=colors.black, leading=11)
    cost_s  = ParagraphStyle('c', fontName=FONT, fontSize=8, textColor=colors.HexColor('#333'), alignment=2)
    tot_s   = ParagraphStyle('tot', fontName=FONT_BOLD, fontSize=8, textColor=BLUE)
    hdr_s   = ParagraphStyle('hdr', fontName=FONT_BOLD, fontSize=10, spaceAfter=4)

    elements.append(Paragraph("Paan Shop - Restock Order", title_s))
    elements.append(Paragraph(f"Generated: {date.today().strftime('%d %B %Y')}", date_s))

    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    local_by_shop = {}
    keep_by_shop  = {}
    market_by_shop = {}

    for shop in SHOPS:
        if shop not in orders_by_shop:
            continue
        for o in orders_by_shop[shop]:
            cat = classify_item(o['item_name'])
            if cat == 'local':
                local_by_shop.setdefault(shop, []).append(o)
            elif cat == 'keep':
                keep_by_shop.setdefault(shop, []).append(o)
            else:
                market_by_shop.setdefault(shop, []).append(o)

    all_shops = [s for s in SHOPS if s in orders_by_shop]

    if not all_shops:
        elements.append(Paragraph("No pending orders.", item_s))
        doc.build(elements)
        buffer.seek(0)
        return buffer.read()

    total_w  = A4[0] - 1.6*cm
    col_loc  = total_w * 0.42
    col_keep = total_w * 0.18
    col_mkt  = total_w * 0.40

    hdr_data = [[
        Paragraph("LOCAL ITEMS", shop_s),
        Paragraph("TIN / KATHA", shop_s),
        Paragraph("MARKET ITEMS", shop_s),
    ]]
    hdr_t = Table(hdr_data, colWidths=[col_loc, col_keep, col_mkt])
    hdr_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), TEAL),
        ('BACKGROUND', (2,0), (2,0), BLUE),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
    ]))
    elements.append(hdr_t)
    elements.append(Spacer(1,2))

    def p(text, style=None):
        return Paragraph(str(text), style or item_s)

    def fmt_qty(q):
        return int(q) if q == int(q) else q

    for shop in all_shops:
        loc  = local_by_shop.get(shop, [])
        keep = keep_by_shop.get(shop, [])
        mkt  = market_by_shop.get(shop, [])

        loc_rows  = [[p(shop, shop_s)]] + [[p(f"  {o['item_name']} - {fmt_qty(o['quantity'])}")] for o in loc]
        keep_rows = [[p(shop, shop_s)]] + [[p(f"  {o['item_name']} - {fmt_qty(o['quantity'])}")] for o in keep]

        mkt_rows = [[p(shop, shop_s), p('')]]
        total_cost = 0
        for o in mkt:
            price = MARKET_ITEMS.get(o['item_name'], 0)
            cost  = price * o['quantity']
            total_cost += cost
            cost_txt = p(f"Rs {cost:,.0f}", cost_s) if (show_costs and price > 0) else p('')
            mkt_rows.append([p(f"  {o['item_name']} - {fmt_qty(o['quantity'])}"), cost_txt])
        if show_costs and total_cost > 0:
            mkt_rows.append([p(f"  Total: Rs {total_cost:,.0f}", tot_s), p('')])

        n = max(len(loc_rows), len(keep_rows), len(mkt_rows))
        while len(loc_rows)  < n: loc_rows.append([p('')])
        while len(keep_rows) < n: keep_rows.append([p('')])
        while len(mkt_rows)  < n: mkt_rows.append([p(''), p('')])

        rows = []
        for i in range(n):
            rows.append([
                loc_rows[i][0],
                keep_rows[i][0],
                mkt_rows[i][0],
                mkt_rows[i][1] if len(mkt_rows[i]) > 1 else p(''),
            ])

        t = Table(rows, colWidths=[col_loc, col_keep, col_mkt*0.72, col_mkt*0.28])
        t.setStyle(TableStyle([
            ('TOPPADDING',    (0,0),(-1,-1), 2),
            ('BOTTOMPADDING', (0,0),(-1,-1), 2),
            ('LEFTPADDING',   (0,0),(-1,-1), 4),
            ('LINEAFTER',     (0,0),(0,-1), 0.3, colors.lightgrey),
            ('LINEAFTER',     (1,0),(1,-1), 0.3, colors.lightgrey),
            ('LINEBELOW',     (0,-1),(-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND',    (0,0),(3,0), colors.HexColor('#e0f2f1')),
        ]))
        elements.append(t)
        elements.append(Spacer(1,2))

    if show_costs:
        elements.append(Spacer(1,8))
        elements.append(Paragraph("Market Cost Summary", hdr_s))
        sum_data = [["Shop","Items","Total Cost"]]
        grand = 0
        for shop in all_shops:
            mkt = market_by_shop.get(shop,[])
            if mkt:
                c = sum(MARKET_ITEMS.get(o['item_name'],0)*o['quantity'] for o in mkt)
                grand += c
                sum_data.append([shop, str(len(mkt)), f"Rs {c:,.0f}"])
        sum_data.append(["TOTAL","",f"Rs {grand:,.0f}"])
        st = Table(sum_data, colWidths=[5*cm,3*cm,5*cm])
        st.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,0), TEAL),
            ('TEXTCOLOR',     (0,0),(-1,0), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), FONT),
            ('FONTNAME',      (0,0),(-1,0), FONT_BOLD),
            ('FONTNAME',      (0,-1),(-1,-1), FONT_BOLD),
            ('BACKGROUND',    (0,-1),(-1,-1), colors.HexColor('#e8f5e9')),
            ('FONTSIZE',      (0,0),(-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),(-1,-2), [colors.white, LIGHT_GRAY]),
            ('GRID',          (0,0),(-1,-1), 0.3, colors.lightgrey),
            ('TOPPADDING',    (0,0),(-1,-1), 4),
            ('BOTTOMPADDING', (0,0),(-1,-1), 4),
            ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ]))
        elements.append(st)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
