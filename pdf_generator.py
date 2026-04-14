from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import date
from database import MARKET_ITEMS, GODOWN_ITEMS, PAAN_ITEMS, SHOPS

IGNORE_ITEMS = [
    'टिन','खजूर','पार्सल कवर','गुलाब','मस्त','डार्क','शिव',
    'चेरी','टूथपिक','सफ़ेद','मैंगो','पिस्ता','स्ट्रॉबेरी','ब्लू बेरी','जेली',
    'खजूर बॉक्स','खड़ा खजूर','खजूर मसाला','अंजीर','ड्राय फ्रूट',
    'मघई बॉक्स','टिशू','कप','कपडा','कथा'
]

KEEP_ITEMS = ['टिन','कथा']

item_prices = {
    'टिन': 3500, 'खजूर': 200, 'पार्सल कवर': 240, 'शिव': 700,
    'चेरी': 280, 'टूथपिक': 125, 'ब्लू बेरी': 230,
    'गुलाब': 200, 'मस्त': 200, 'डार्क': 150,
    'सफ़ेद': 210, 'मैंगो': 215, 'पिस्ता': 215,
    'स्ट्रॉबेरी': 215, 'जेली': 250,
    'खजूर बॉक्स': 50, 'खड़ा खजूर': 300,
    'खजूर मसाला': 300, 'अंजीर': 800, 'ड्राय फ्रूट': 800,
    'मघई बॉक्स': 0, 'टिशू': 0, 'कप': 0, 'कपडा': 0, 'कथा': 0
}

try:
    pdfmetrics.registerFont(TTFont('Hindi', 'fonts/NotoSansDevanagari-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('HindiBold', 'fonts/NotoSansDevanagari-Bold.ttf'))
    FONT = 'Hindi'
    FONT_BOLD = 'HindiBold'
except Exception as e:
    print("Font load failed:", e)
    FONT = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

TEAL  = colors.HexColor('#00695c')   # dark teal - godown
GREEN = colors.HexColor('#1565c0')   # blue - market+paan
BROWN = colors.HexColor('#4e342e')   # brown - morning items
LIGHT = colors.HexColor('#f5f5f5')

# ── Column 3: Morning packing items (Tin, Cover, Masala, Katha) ──
MORNING_ITEMS = [
    'टिन', 'टिन / मसाला', 'पार्सल कवर', 'कथा',
    'tin', 'katha',
]



def generate_restock_pdf(orders, show_costs=False):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=0.7*cm, rightMargin=0.7*cm,
                             topMargin=1.2*cm, bottomMargin=0.8*cm)
    elements = []

    title_s = ParagraphStyle('t',  fontName=FONT_BOLD, fontSize=13, spaceAfter=4, alignment=1)
    date_s  = ParagraphStyle('d',  fontName=FONT, fontSize=8, spaceAfter=8, alignment=1, textColor=colors.gray)
    shop_s  = ParagraphStyle('sh', fontName=FONT_BOLD, fontSize=9, textColor=colors.white)
    item_s  = ParagraphStyle('i',  fontName=FONT, fontSize=8, textColor=colors.black, leading=11)
    hdr_s   = ParagraphStyle('h',  fontName=FONT_BOLD, fontSize=10, spaceAfter=4)

    elements.append(Paragraph("Paan Shop — Restock Sheet", title_s))
    elements.append(Paragraph(f"Date: {date.today().strftime('%d %B %Y')}", date_s))

    # Organise orders by shop then by column
    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    godown_by_shop     = {}
    mkt_paan_by_shop   = {}
    morning_by_shop    = {}

    for shop in SHOPS:
        if shop not in orders_by_shop:
            continue

        for o in orders_by_shop[shop]:
            item = o['item_name'].strip()
            
            if item == '__EXTRA__':
                continue

            #  COLUMN 3 (TIN/KATHA)
            if item in KEEP_ITEMS:
                morning_by_shop.setdefault(shop, []).append(o)
                continue

            #  COLUMN 1 (LOCAL / IGNORED ITEMS)
            if item in IGNORE_ITEMS:
                godown_by_shop.setdefault(shop, []).append(o)
                continue

            #  COLUMN 2 (MARKET)
            mkt_paan_by_shop.setdefault(shop, []).append(o)
            
            
    all_shops = [s for s in SHOPS if s in orders_by_shop]
    if not all_shops:
        elements.append(Paragraph("No pending orders.", item_s))
        doc.build(elements)
        buffer.seek(0)
        return buffer.read()

    # Column widths — godown wider, morning narrower
    total_w = A4[0] - 1.4*cm
    col_g = total_w * 0.38   # Godown
    col_m = total_w * 0.40   # Market+Paan (with cost col)
    col_k = total_w * 0.22   # Morning (Tin/Cover/Masala/Katha)

    # Header row
    hdr_data = [[
        Paragraph("GODOWN / गोदाम", shop_s),
        Paragraph("MARKET + PAAN / मार्केट+पान", shop_s),
        Paragraph("TIN / COVER / KATHA", shop_s),
    ]]
    hdr_t = Table(hdr_data, colWidths=[col_g, col_m, col_k])
    hdr_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(0,0), TEAL),
        ('BACKGROUND',    (1,0),(1,0), GREEN),
        ('BACKGROUND',    (2,0),(2,0), BROWN),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ('LINEAFTER',     (0,0),(1,0), 0.5, colors.white),
    ]))
    elements.append(hdr_t)
    elements.append(Spacer(1, 3))

    def p(text, style=None):
        return Paragraph(str(text), style or item_s)

    def fmt(q):
        return int(q) if float(q) == int(float(q)) else q

    for shop in all_shops:
        gdn  = godown_by_shop.get(shop, [])
        mkt  = mkt_paan_by_shop.get(shop, [])
        mrn  = morning_by_shop.get(shop, [])

        # Godown column rows
        g_rows = [[p(shop, shop_s)]]
        for o in gdn:
            item = o['item_name']
            qty = o['quantity']

            price = item_prices.get(item, 0)
            cost = price * qty if price else 0

            text = f"  {item} - {fmt(qty)}"
            if cost:
                text += f" (₹{int(cost)})"

            g_rows.append([p(text)])

        # Market+Paan column rows (with optional cost)
        m_rows = [[p(shop, shop_s), p('')]]
        for o in mkt:
            ctxt = p('')  # no cost shown
            m_rows.append([p(f"  {o['item_name']} - {fmt(o['quantity'])}"), ctxt])
        

        # Morning column r
        k_rows = [[p(shop, shop_s)]]

        tin_total = 0

        for o in mrn:
            item = o['item_name']
            qty = o['quantity']

            if item == 'टिन':
                tin_total += qty

            k_rows.append([p(f"  {item} - {fmt(qty)}")])

        # 👉 add cover masala at top
        if tin_total:
            cover = tin_total * 0.75
            k_rows.insert(1, [p(f"  कवर मसाला - {cover:.2f}")])
        

        
        
        # Pad to same height
        n = max(len(g_rows), len(m_rows), len(k_rows))
        while len(g_rows) < n: g_rows.append([p('')])
        while len(m_rows) < n: m_rows.append([p(''), p('')])
        while len(k_rows) < n: k_rows.append([p('')])

        # Combine into one table per shop
        combined = []
        for i in range(n):
            combined.append([
                g_rows[i][0],
                m_rows[i][0],
                m_rows[i][1] if len(m_rows[i]) > 1 else p(''),
                k_rows[i][0],
            ])

        t = Table(combined, colWidths=[col_g, col_m*0.72, col_m*0.28, col_k])
        t.setStyle(TableStyle([
            ('TOPPADDING',    (0,0),(-1,-1), 2),
            ('BOTTOMPADDING', (0,0),(-1,-1), 2),
            ('LEFTPADDING',   (0,0),(-1,-1), 4),
            ('LINEAFTER',     (0,0),(0,-1), 0.4, colors.HexColor('#b2dfdb')),
            ('LINEAFTER',     (2,0),(2,-1), 0.4, colors.HexColor('#bbdefb')),
            ('LINEBELOW',     (0,-1),(-1,-1), 0.6, colors.lightgrey),
            # Shop header row background
            ('BACKGROUND',    (0,0),(0,0), colors.HexColor('#e0f2f1')),
            ('BACKGROUND',    (1,0),(2,0), colors.HexColor('#e3f2fd')),
            ('BACKGROUND',    (3,0),(3,0), colors.HexColor('#efebe9')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 2))
        
        extras = [o for o in orders_by_shop.get(shop,[]) if o['item_name'] == '__EXTRA__']
        if extras:
            note_text = " | ".join(o.get('extra_note','') for o in extras if o.get('extra_note'))
            if note_text:
                elements.append(Paragraph(f"📝 {shop}: {note_text}", item_s))


    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
