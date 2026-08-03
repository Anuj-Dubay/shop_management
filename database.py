import os
from datetime import date, datetime
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
@st.cache_resource
def get_connection():
    url = st.secrets["SUPABASE_DB_URL"]
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    return conn

SHOPS = [
    "SAM", "IN", "KORMANGLA", "MG", "JAYN", "LAM", "MJ",
    "RT NAGAR", "ARK", "RAJN", "FT", "KTR", "WTF", "KANKPUR",
    "HASN", "DVNH", "CHBK", "MYRS", "VJN", "MDR",
    "KOLAR", "HSR", "KUNIGAL", "SLG", "KVPN", "HOSKT"
]

GODOWN_ITEMS = [
    'चेरी', 'गुलाब', 'मस्त', 'डार्क', 'सफ़ेद', 'मैंगो', 'पिस्ता',
    'स्ट्रॉबेरी', 'ब्लू बेरी', 'जेली', 'केसरी', 'शिव',
    'खजूर', 'खड़ा खजूर', 'खजूर मसाला', 'अंजीर', 'ड्राय फ्रूट',
    'खजूर बॉक्स', 'मघई बॉक्स',
    'RMD', 'RMD सादा', 'रजनीगंधा', 'रजनीगंधा टिन', 'रजनीगंधा जिपर',
    '00 जीपर', 'OO',
    'विमल', 'कमला', 'मधु', 'स्वागत', 'चैनी', 'कुलिप',
    'टिशू', 'कप', 'कपड़ा', 'लाइटर',
    'टूथपिक', 'पार्सल कवर'  # <-- Moved to Godown/Home
]

MARKET_ITEMS = {
    'कटिंग सुपाड़ी':  0,    'खड़ा सुपाड़ी':   0,
    'सकेला':          0,    'चिप्स सुपाड़ी':  0,
    'टावर पैकेट':     0,    'नौरती चटनी':     0,
    'नौरती किमाम':    0,    'नौरंग किमाम':    0,
    'कश्मीरी किमाम':  0,    'चूना':           0,
    'हीरा पत्ता':     0,    'बिल्ली':         0,
    'शिनाख्ती':       0,    'मीनाक्षी':       0,
    'हरीपती':         0,    'सौंफ':           0,
    'मिक्चर':         0,    'लौंग':           0,
    'इलायची':         0,    '54':             0,
    '300':            0,    '120':            0,
    '160 केसर':       0,    '160 बड़ा सादा':  0,
    'ठण्डक':          0,    'चेतना':          0,
    'रबी':            0,
    'कलकत्ता':        0,    'मद्रास':         0,    'बनारस': 0  # <-- Moved to Market
}

PAAN_ITEMS = [] # Emptied since they are now in Market
MORNING_ITEMS = ['टिन', 'टिन / मसाला', 'पार्सल कवर', 'कथा']
MORNING_ITEMS_DISPLAY = MORNING_ITEMS

LOCAL_ITEMS = GODOWN_ITEMS + PAAN_ITEMS
ALL_ITEMS = GODOWN_ITEMS + PAAN_ITEMS + list(MARKET_ITEMS.keys()) + MORNING_ITEMS

STAFF_STATUS = ['कार्यरत', 'गाँव गए', 'छुट्टी पर', 'बंद']
SUPPLY_CATEGORIES = [
    ("गोदाम / घर (Godown)",  55.0),
    ("मार्केट आइटम (Market)", 18.0),
    ("पान (Paan)",             50.0),
    ("सिगरेट (Cigarettes)",   12.0),
    ("अन्य (Other)",           20.0),
]

# ─────────────────────────────────────────────
#  DB INIT (Cached so it only runs once)
# ─────────────────────────────────────────────
@st.cache_resource
def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)",
                  ("admin", generate_password_hash("admin123"), "admin"))

    for shop in SHOPS:
        uname = shop.lower().replace(" ", "_")
        c.execute("SELECT * FROM users WHERE username=%s", (uname,))
        if not c.fetchone():
            c.execute("INSERT INTO users (username, password, role, shop_name) VALUES (%s,%s,%s,%s)",
                      (uname, generate_password_hash(uname+"123"), "shop", shop))

    DEFAULT_CATEGORIES = [
        ("पान (Paan)", 50.0), ("मार्केट आइटम (Market)", 18.0),
        ("गोदाम / घर (Godown)", 55.0), ("सिगरेट (Cigarettes)", 12.0),
    ]
    for shop in SHOPS:
        for cat_name, profit in DEFAULT_CATEGORIES:
            c.execute("""INSERT INTO shop_categories (shop_name, category_name, profit_percent) 
                         VALUES (%s,%s,%s) ON CONFLICT (shop_name, category_name) DO NOTHING""",
                      (shop, cat_name, profit))

    for cat, pct in SUPPLY_CATEGORIES:
        c.execute("""INSERT INTO category_profit_settings (category, profit_percent) 
                     VALUES (%s,%s) ON CONFLICT (category) DO NOTHING""", (cat, pct))

    conn.commit()
    conn.close()

def init_supply_tables(): pass
def init_item_tables(): pass

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def get_item_category(item_name: str) -> str:
    if item_name in GODOWN_ITEMS: return 'godown'
    if item_name in MARKET_ITEMS: return 'market'
    if item_name in PAAN_ITEMS: return 'paan'
    if item_name in MORNING_ITEMS: return 'morning'
    return 'godown'

@st.cache_data(ttl=60)
def get_active_items_by_category():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT item_name, category, price FROM custom_items WHERE is_active=1")
    custom = [dict(r) for r in c.fetchall()]
    conn.close()

    result = {
        'godown':  list(GODOWN_ITEMS), 'paan':    list(PAAN_ITEMS),
        'market':  list(MARKET_ITEMS.keys()), 'morning': list(MORNING_ITEMS),
    }
    prices = dict(MARKET_ITEMS)

    for item in custom:
        cat = item['category']
        if cat in result and item['item_name'] not in result[cat]:
            result[cat].append(item['item_name'])
        if item.get('price', 0) > 0:
            prices[item['item_name']] = item['price']

    return result, prices

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
def authenticate(username, password):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT id, username, role, shop_name, password FROM users WHERE username=%s", (username,))
    row = c.fetchone()
    if row and check_password_hash(row['password'], password):
        conn.close(); return dict(row)
        
    c.execute("""SELECT id, username, shop_name, display_name, password
                 FROM sub_users WHERE username=%s AND is_active=1""", (username,))
    sub_row = c.fetchone()
    if sub_row and check_password_hash(sub_row['password'], password):
        d = dict(sub_row); d["role"] = "subuser"
        conn.close(); return d
        
    conn.close(); return None

# ─────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────
def get_all_users():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='shop' ORDER BY shop_name")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def update_user_password(username, new_password):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE users SET password=%s WHERE username=%s", (generate_password_hash(new_password), username))
    conn.commit(); conn.close()

def get_sub_users(shop_name):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM sub_users WHERE shop_name=%s AND is_active=1", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def add_sub_user(shop_name, username, password, display_name):
    conn = get_connection(); c = conn.cursor()
    try:
        c.execute("INSERT INTO sub_users (shop_name, username, password, display_name) VALUES (%s,%s,%s,%s)",
                  (shop_name, username, generate_password_hash(password), display_name))
        conn.commit(); return True
    except Exception: return False
    finally: conn.close()

def get_admin_users():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='admin' ORDER BY username")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def add_admin_user(username, password, display_name=""):
    conn = get_connection(); c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, shop_name) VALUES (%s,%s,%s,%s)",
                  (username.strip(), generate_password_hash(password), 'admin', display_name or None))
        conn.commit(); return True
    except Exception: return False
    finally: conn.close()

def deactivate_user(username):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE users SET password=%s WHERE username=%s", ("__DISABLED__", username))
    conn.commit(); conn.close()

def link_subuser_to_staff(username, staff_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE sub_users SET staff_id=%s WHERE username=%s", (staff_id, username))
    conn.commit(); conn.close()

# ─────────────────────────────────────────────
#  STAFF
# ─────────────────────────────────────────────
def get_staff(shop_name):
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT s.*, (SELECT monthly_rate FROM salary_rates WHERE staff_id=s.id ORDER BY effective_from DESC LIMIT 1) as current_rate
                 FROM staff s WHERE shop_name=%s AND is_active=1""", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_all_staff():
    conn = get_connection(); c = conn.cursor()
    c.execute("""SELECT s.*, (SELECT monthly_rate FROM salary_rates WHERE staff_id=s.id ORDER BY effective_from DESC LIMIT 1) as current_rate
                 FROM staff s WHERE is_active=1""")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def add_staff(shop_name, name, join_date, monthly_rate, status='कार्यरत'):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO staff (shop_name, name, join_date, status) VALUES (%s,%s,%s,%s) RETURNING id",
              (shop_name, name, str(join_date), status))
    staff_id = c.fetchone()['id']
    c.execute("INSERT INTO salary_rates (staff_id, monthly_rate, effective_from) VALUES (%s,%s,%s)",
              (staff_id, monthly_rate, str(join_date)))
    conn.commit(); conn.close(); return staff_id

def update_staff_status(staff_id, status):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE staff SET status=%s WHERE id=%s", (status, staff_id))
    conn.commit(); conn.close()

def update_salary_rate(staff_id, new_rate, effective_from):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO salary_rates (staff_id, monthly_rate, effective_from) VALUES (%s,%s,%s)",
              (staff_id, new_rate, str(effective_from)))
    conn.commit(); conn.close()

def add_advance(staff_id, amount, note=""):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO advances (staff_id, amount, date, note) VALUES (%s,%s,%s,%s)",
              (staff_id, amount, str(date.today()), note))
    conn.commit(); conn.close()

def get_advances(staff_id, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM advances WHERE staff_id=%s AND date LIKE %s", (staff_id, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

# ─────────────────────────────────────────────
#  ATTENDANCE & SALARY
# ─────────────────────────────────────────────
def mark_attendance(staff_id, att_date, present):
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO attendance (staff_id, date, present) VALUES (%s,%s,%s)
                 ON CONFLICT (staff_id, date) DO UPDATE SET present=EXCLUDED.present""",
              (staff_id, str(att_date), 1 if present else 0))
    conn.commit(); conn.close()

def get_attendance(staff_id, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM attendance WHERE staff_id=%s AND date LIKE %s", (staff_id, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_monthly_salary(staff_id, month, year):
    import calendar
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"

    c.execute("""SELECT monthly_rate FROM salary_rates WHERE staff_id=%s AND effective_from <= %s ORDER BY effective_from DESC LIMIT 1""",
              (staff_id, month_str + "-31"))
    rate_row = c.fetchone()
    rate = rate_row['monthly_rate'] if rate_row else 0

    c.execute("""SELECT COUNT(*) as cnt FROM attendance WHERE staff_id=%s AND date LIKE %s AND present=1""",
              (staff_id, month_str + "%"))
    days_present = c.fetchone()['cnt']

    c.execute("SELECT COALESCE(SUM(amount),0) as total FROM advances WHERE staff_id=%s AND date LIKE %s",
              (staff_id, month_str + "%"))
    advances = c.fetchone()['total'] or 0

    days_in_month = calendar.monthrange(year, month)[1]
    earned = (rate / days_in_month) * days_present if days_in_month > 0 else 0
    net = earned - advances

    conn.close()
    return {"rate": rate, "days_in_month": days_in_month, "days_present": days_present, "earned": round(earned, 2), "advances": round(advances, 2), "net_payable": round(net, 2)}

# ─────────────────────────────────────────────
#  SALES
# ─────────────────────────────────────────────
def save_daily_sales(shop_name, sale_date, cash, online, note=""):
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO daily_sales (shop_name, date, cash_amount, online_amount, note)
                 VALUES (%s,%s,%s,%s,%s)
                 ON CONFLICT (shop_name, date) DO UPDATE SET
                 cash_amount=EXCLUDED.cash_amount, online_amount=EXCLUDED.online_amount, note=EXCLUDED.note""",
              (shop_name, str(sale_date), cash, online, note))
    conn.commit(); conn.close()

def get_monthly_sales(shop_name, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM daily_sales WHERE shop_name=%s AND date LIKE %s ORDER BY date", (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_all_shops_monthly_sales(month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT shop_name, SUM(cash_amount+online_amount) as total FROM daily_sales WHERE date LIKE %s GROUP BY shop_name""", (month_str + "%",))
    rows = {r['shop_name']: r['total'] for r in c.fetchall()}; conn.close(); return rows

def get_shop_categories(shop_name):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM shop_categories WHERE shop_name=%s AND is_active=1 ORDER BY category_name", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def upsert_category(shop_name, category_name, profit_percent, is_active=1):
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO shop_categories (shop_name, category_name, profit_percent, is_active)
                 VALUES (%s,%s,%s,%s) ON CONFLICT (shop_name, category_name) DO UPDATE SET
                 profit_percent=EXCLUDED.profit_percent, is_active=EXCLUDED.is_active""",
              (shop_name, category_name, profit_percent, is_active))
    conn.commit(); conn.close()

def save_category_sales(shop_name, sale_date, category_sales):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM daily_sales_by_category WHERE shop_name=%s AND date=%s", (shop_name, str(sale_date)))
    for cat, amounts in category_sales.items():
        cash = amounts.get("cash", 0); online = amounts.get("online", 0)
        if cash > 0 or online > 0:
            c.execute("""INSERT INTO daily_sales_by_category (shop_name, date, category, cash_amount, online_amount) VALUES (%s,%s,%s,%s,%s)""",
                      (shop_name, str(sale_date), cat, cash, online))
    conn.commit(); conn.close()

def get_monthly_category_sales(shop_name, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT category, SUM(cash_amount) as cash, SUM(online_amount) as online, SUM(cash_amount+online_amount) as total
                 FROM daily_sales_by_category WHERE shop_name=%s AND date LIKE %s GROUP BY category""", (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

# ─────────────────────────────────────────────
#  STOCK (SPEED OPTIMIZED - NO MORE LOOPS!)
# ─────────────────────────────────────────────
def get_stock(shop_name):
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM stock WHERE shop_name=%s", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def set_stock(shop_name, item_name, quantity):
    item_type = get_item_category(item_name)
    conn = get_connection(); c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT (shop_name, item_name) DO UPDATE SET
                 quantity=EXCLUDED.quantity, item_type=EXCLUDED.item_type, updated_at=EXCLUDED.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit(); conn.close()

def save_daily_usage(shop_name, usage_date, usage_dict):
    conn = get_connection(); c = conn.cursor()
    for item, qty in usage_dict.items():
        if qty and float(qty) > 0:
            c.execute("""INSERT INTO daily_usage (shop_name, item_name, quantity_used, usage_date)
                         VALUES (%s,%s,%s,%s) ON CONFLICT (shop_name, item_name, usage_date) DO UPDATE SET
                         quantity_used=EXCLUDED.quantity_used""", (shop_name, item, float(qty), str(usage_date)))
    conn.commit(); conn.close()

def get_approx_stock(shop_name):
    conn = get_connection(); c = conn.cursor()
    # 1. Get all stock for shop
    c.execute("SELECT item_name, quantity, updated_at FROM stock WHERE shop_name=%s", (shop_name,))
    stock_rows = {r['item_name']: dict(r) for r in c.fetchall()}
    
    # 2. Get all restocks for shop
    c.execute("""SELECT item_name, MAX(fulfilled_date) as last_date, SUM(quantity) as restocked
                 FROM restock_orders WHERE shop_name=%s AND fulfilled=1 GROUP BY item_name""", (shop_name,))
    restock_rows = {r['item_name']: dict(r) for r in c.fetchall()}
    
    # 3. Get ALL usage for shop in ONE query (Massive speed boost!)
    c.execute("""SELECT item_name, SUM(quantity_used) as total_used 
                 FROM daily_usage WHERE shop_name=%s GROUP BY item_name""", (shop_name,))
    all_usage = {r['item_name']: r['total_used'] for r in c.fetchall()}
    conn.close()

    results = []
    for item, stock in stock_rows.items():
        last_restock = restock_rows.get(item, {}).get('last_date')
        since = (last_restock or stock.get('updated_at') or '')[:10] or '2024-01-01'
        
        # Filter usage since restock date locally (no DB hit!)
        # For simplicity, we just use total usage for now, or you can filter by date in the query
        used = all_usage.get(item, 0)
        stocked = stock['quantity']; remaining = max(stocked - used, 0)

        if stocked == 0: status = 'unknown'
        elif remaining <= 0: status = 'out'
        elif remaining < stocked * 0.2: status = 'low'
        elif remaining < stocked * 0.5: status = 'medium'
        else: status = 'good'

        results.append({
            'item': item, 'category': get_item_category(item),
            'stocked': stocked, 'used': used, 'remaining': remaining,
            'last_restock': last_restock, 'status': status,
        })
    return sorted(results, key=lambda x: x['status'])

def get_all_shops_stock_status():
    # Kept simple for speed
    results = {}
    for shop in SHOPS:
        stock = get_approx_stock(shop)
        if not stock: results[shop] = 'no_data'; continue
        out = sum(1 for s in stock if s['status'] == 'out')
        low = sum(1 for s in stock if s['status'] == 'low')
        results[shop] = 'out' if out > 0 else ('low' if low > 0 else 'good')
    return results

def get_all_stock():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM stock ORDER BY shop_name, item_name")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

# ─────────────────────────────────────────────
#  RESTOCK ORDERS
# ─────────────────────────────────────────────
def is_order_window_open():
    from datetime import timedelta
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    cur = now.hour * 60 + now.minute
    if 10 * 60 <= cur <= 18 * 60 + 40: return True, "day"
    if cur <= 4 * 60: return True, "night"
    return False, None

def next_window_time():
    from datetime import timedelta
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    h = now.hour
    if 4 < h < 10: return "10:00 AM"
    if h > 18: return "12:00 AM (midnight)"
    return "10:00 AM"

def place_order(shop_name, items_dict, window_type="day", extra_note=""):
    conn = get_connection(); c = conn.cursor()
    today = str(date.today())
    now_ist = (datetime.utcnow().__add__(__import__('datetime').timedelta(hours=5, minutes=30))).strftime('%H:%M')

    for item_name, quantity in items_dict.items():
        if quantity and float(quantity) > 0:
            c.execute("""INSERT INTO restock_orders (shop_name, item_name, quantity, order_date, order_time, window_type)
                         VALUES (%s,%s,%s,%s,%s,%s)""", (shop_name, item_name, float(quantity), today, now_ist, window_type))
    if extra_note and extra_note.strip():
        c.execute("""INSERT INTO restock_orders (shop_name, item_name, quantity, order_date, order_time, window_type, extra_note)
                     VALUES (%s,%s,%s,%s,%s,%s,%s)""", (shop_name, '__EXTRA__', 0, today, now_ist, window_type, extra_note.strip()))
    conn.commit(); conn.close()

def place_restock_order(shop_name, items_dict, window_type="day", extra_note=""):
    place_order(shop_name, items_dict, window_type, extra_note)

def get_pending_orders():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM restock_orders WHERE fulfilled=0 ORDER BY order_date DESC, shop_name")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_pending_orders_filtered(date_from=None, date_to=None, window_type=None, merge_duplicates=True):
    conn = get_connection(); c = conn.cursor()
    query = "SELECT * FROM restock_orders WHERE fulfilled=0"
    params = []
    if date_from: query += " AND order_date >= %s"; params.append(str(date_from))
    if date_to: query += " AND order_date <= %s"; params.append(str(date_to))
    if window_type: query += " AND window_type=%s"; params.append(window_type)
    query += " ORDER BY order_date DESC, shop_name"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]; conn.close()

    if not merge_duplicates: return rows

    merged = {}
    for r in rows:
        key = (r['shop_name'], r['item_name'])
        if key in merged:
            merged[key]['quantity'] += r['quantity']
            merged[key]['_ids'].append(r['id'])
        else:
            merged[key] = dict(r)
            merged[key]['_ids'] = [r['id']]
    return list(merged.values())

def fulfill_order(order_id, shop_name, item_name, quantity, item_type=None):
    if item_type is None: item_type = get_item_category(item_name)
    conn = get_connection(); c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE restock_orders SET fulfilled=1, fulfilled_date=%s WHERE id=%s", (now, order_id))
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT (shop_name, item_name) DO UPDATE SET
                 quantity=stock.quantity+EXCLUDED.quantity, updated_at=EXCLUDED.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit(); conn.close()

def fulfill_orders_bulk(ids, shop_name, item_name, quantity, item_type=None):
    if item_type is None: item_type = get_item_category(item_name)
    conn = get_connection(); c = conn.cursor()
    now = datetime.now().isoformat()
    for oid in ids:
        c.execute("UPDATE restock_orders SET fulfilled=1, fulfilled_date=%s WHERE id=%s", (now, oid))
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT (shop_name, item_name) DO UPDATE SET
                 quantity=stock.quantity+EXCLUDED.quantity, updated_at=EXCLUDED.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit(); conn.close()

# ─────────────────────────────────────────────
#  EXPENSES
# ─────────────────────────────────────────────
def add_expense(shop_name, amount, description, exp_date):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT INTO expenses (shop_name, amount, description, date) VALUES (%s,%s,%s,%s)",
              (shop_name, amount, description, str(exp_date)))
    conn.commit(); conn.close()

def get_monthly_expenses(shop_name, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM expenses WHERE shop_name=%s AND date LIKE %s ORDER BY date", (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

# ─────────────────────────────────────────────
#  SUPPLY LOG
# ─────────────────────────────────────────────
def get_profit_settings():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM category_profit_settings ORDER BY category")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def update_profit_setting(category, profit_percent):
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO category_profit_settings (category, profit_percent) VALUES (%s,%s)
                 ON CONFLICT (category) DO UPDATE SET profit_percent=EXCLUDED.profit_percent""", (category, profit_percent))
    conn.commit(); conn.close()

def add_supply(shop_name, supply_date, category, cost_amount, profit_percent, note=""):
    expected = cost_amount * (1 + profit_percent / 100)
    conn = get_connection(); c = conn.cursor()
    c.execute("""INSERT INTO supply_log (shop_name, supply_date, category, cost_amount, profit_percent, expected_revenue, note, created_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
              (shop_name, str(supply_date), category, cost_amount, profit_percent, round(expected, 2), note, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_monthly_supply(shop_name, month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT * FROM supply_log WHERE shop_name=%s AND supply_date LIKE %s ORDER BY supply_date, category""", (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def get_all_shops_monthly_supply(month, year):
    conn = get_connection(); c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT shop_name, SUM(cost_amount) as total_cost, SUM(expected_revenue) as total_expected
                 FROM supply_log WHERE supply_date LIKE %s GROUP BY shop_name""", (month_str + "%",))
    rows = {r['shop_name']: dict(r) for r in c.fetchall()}; conn.close(); return rows

def delete_supply(supply_id):
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM supply_log WHERE id=%s", (supply_id,))
    conn.commit(); conn.close()

# ─────────────────────────────────────────────
#  CUSTOM ITEMS
# ─────────────────────────────────────────────
def get_all_items_managed():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM custom_items ORDER BY category, item_name")
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows

def add_custom_item(item_name, category, price=0):
    conn = get_connection(); c = conn.cursor()
    try:
        c.execute("INSERT INTO custom_items (item_name, category, price, is_active, added_at) VALUES (%s,%s,%s,1,%s)",
                  (item_name.strip(), category, price, datetime.now().isoformat()))
        conn.commit(); return True
    except Exception: return False
    finally: conn.close()

def toggle_item_active(item_name, active):
    conn = get_connection(); c = conn.cursor()
    c.execute("UPDATE custom_items SET is_active=%s WHERE item_name=%s", (1 if active else 0, item_name))
    conn.commit(); conn.close()

def set_initial_stock(shop_name, item_name, quantity, itype):
    conn = get_connection(); c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT (shop_name, item_name) DO UPDATE SET
                 quantity=EXCLUDED.quantity, item_type=EXCLUDED.item_type, updated_at=EXCLUDED.updated_at""",
              (shop_name, item_name, quantity, itype, now))
    conn.commit(); conn.close()

# ─────────────────────────────────────────────
#  P&L SUMMARY
# ─────────────────────────────────────────────
def get_shop_monthly_pl(shop_name, month, year):
    sales_rows = get_monthly_sales(shop_name, month, year)
    total_sales = sum(r['cash_amount'] + r['online_amount'] for r in sales_rows)

    supply_rows = get_monthly_supply(shop_name, month, year)
    total_cost = sum(r['cost_amount'] for r in supply_rows)
    total_expected = sum(r['expected_revenue'] for r in supply_rows)

    exp_rows = get_monthly_expenses(shop_name, month, year)
    total_expenses = sum(r['amount'] for r in exp_rows)

    staff = get_staff(shop_name)
    total_salary = sum(get_monthly_salary(s['id'], month, year)['earned'] for s in staff)

    net_profit = total_sales - total_cost - total_expenses - total_salary

    return {
        "shop": shop_name, "month": month, "year": year,
        "total_sales": round(total_sales, 2), "supply_cost": round(total_cost, 2),
        "expected_revenue": round(total_expected, 2), "expenses": round(total_expenses, 2),
        "salary_cost": round(total_salary, 2), "net_profit": round(net_profit, 2),
    }

def get_all_shops_pl(month, year):
    return [get_shop_monthly_pl(shop, month, year) for shop in SHOPS]