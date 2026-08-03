from weasyprint import HTML
from io import BytesIO
from database import MARKET_ITEMS, GODOWN_ITEMS, PAAN_ITEMS, MORNING_ITEMS

def generate_restock_pdf(orders, show_costs=True):
    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    def build_section(mode_title, filter_func):
        html = f'<div class="title-bar">{mode_title}</div>'
        html += '<div class="section">'
        
        for shop, shop_orders in orders_by_shop.items():
            filtered_orders = filter_func(shop_orders)
            if not filtered_orders: continue
            
            html += '<div class="shop">'
            html += f'<div class="shop-header">{shop}</div>'
            
            total_cost = 0
            for o in filtered_orders:
                item = o['item_name']
                qty = o['quantity']
                if item == '__EXTRA__': continue
                
                cost = MARKET_ITEMS.get(item, 0) * qty
                total_cost += cost
                
                text = f"{item} - {qty}"    
                html += f'<div class="item">{text}</div>'
                
            for o in filtered_orders:
                if o.get('item_name') == '__EXTRA__' and o.get('extra_note'):
                    html += f'<div class="item">• {o["extra_note"]}</div>'
                    
            html += '</div>'
            
        html += '</div>'
        return html

    def filter_all(orders): 
        return [o for o in orders if o['item_name'] != '__EXTRA__'] + [o for o in orders if o['item_name'] == '__EXTRA__']
        
    def filter_market(orders): 
        return [o for o in orders if o['item_name'] in MARKET_ITEMS or o['item_name'] in PAAN_ITEMS]
        
    def filter_morning(orders): 
        return [o for o in orders if o['item_name'] in MORNING_ITEMS]

    html_content = """
    <style>
        @font-face { font-family: 'NotoSansDevanagari'; src: url('file:///usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf'); }
        @page { size: A4; margin: 1cm; }
        body { font-family: 'NotoSansDevanagari', sans-serif; }
        .section { column-count: 4; column-gap: 0.3cm; }
        .shop { border: 0.6px solid black; margin-bottom: 0.2cm; break-inside: avoid; }
        .shop-header { background-color: yellow; text-align: center; font-weight: bold; border-bottom: 0.5px solid black; padding: 2px; font-family: Helvetica, Arial, sans-serif; }
        .item { border-bottom: 0.2px solid black; padding: 1px 2px; font-size: 8pt; text-align: center; }
        .item:last-child { border-bottom: none; }
        .title-bar { background-color: yellow; border: 0.8px solid black; text-align: center; font-weight: bold; font-size: 16pt; margin-bottom: 0.4cm; padding: 5px; font-family: Helvetica, Arial, sans-serif; }
        .page-break { break-before: page; }
    </style>
    """
    html_content += build_section("ALL ITEMS", filter_all)
    html_content += '<div class="page-break"></div>'
    html_content += build_section("MARKET ITEMS", filter_market)
    html_content += '<div class="page-break"></div>'
    html_content += build_section("TIN & KATHA", filter_morning)

    buffer = BytesIO()
    HTML(string=html_content).write_pdf(buffer)
    buffer.seek(0)
    return buffer.read()