import os
import sqlite3
from datetime import date, datetime
import streamlit as st

DB_PATH = "paan_manager.db"

SHOPS = ["SAM","IN","KORMANGLA","MG","JAYN","LAM","MJ","RT NAGAR","ARK","RAJN",
         "FT","KTR","WTF","KANKPUR","HASN","DVNH","CHBK","MYRS","VJN","MDR",
         "KOLAR","HSR","KUNIGAL","SLG","KVPN","HOSKT"]

# ── Item Lists (from order form) ──────────────────────

# Paan items — what shops make paan from
PAAN_ITEMS = [
    'कलकत्ता', 'मद्रास', 'बनारस',
]

# Market items — bought from market (with prices)
MARKET_ITEMS = {
    'कटिंग सुपाड़ी': 0, 'खड़ा सुपाड़ी': 300, 'सकेला': 0,
    'चिप्स सुपाड़ी': 0, 'केसरी': 0, 'टावर पैकेट': 0,
    'नौरती चटनी': 0, 'नौरती किमाम': 0, 'नौरंग किमाम': 0,
    'कश्मीरी किमाम': 0, 'चूना': 0, 'हीरा पत्ता': 0,
    'बिल्ली': 0, 'शिनाख्ती': 0, 'मीनाक्षी': 0, 'हरीपती': 0,
    'सौंफ': 0, 'मिक्चर': 0, 'लौंग': 0, 'इलायची': 0,
    'OO': 0, '00 जीपर': 0, 'ठप्पा': 0, 'चेतना': 0,
    'रबी': 0, 'लाइटर': 0, '54': 0, '300': 0,
    '120': 0, '160': 0, 'बड़ा सादा': 0,
    # Original market items with prices
    'टूथपिक': 125, 'पार्सल कवर': 240,
    'गुलाब': 200, 'मस्त': 200, 'डार्क': 150, 'सफ़ेद': 210,
    'मैंगो': 215, 'पिस्ता': 215, 'स्ट्रॉबेरी': 215, 'ब्लू बेरी': 230,
    'जेली': 250, 'खजूर बॉक्स': 50, 'खजूर मसाला': 300,
    'अंजीर': 800, 'ड्राय फ्रूट': 800,
}

# Godown items — supplied from your godown
GODOWN_ITEMS = [
    'RMD', 'सादा', 'रजनीगंधा', 'रजनीगंधा टिन', 'रजनीगंधा जिपर',
    'विमल', 'कमला', 'मधु', 'स्वागत', 'चैनी', 'कुलिप',
    'टिन / मसाला', 'चेरी', 'खजूर', 'शिवा',
    'मघई बॉक्स', 'केसर', 'टिशू', 'कप', 'कपड़ा', 'कथा',
]

# For backward compatibility
LOCAL_ITEMS = PAAN_ITEMS + GODOWN_ITEMS

ALL_ITEMS = PAAN_ITEMS + GODOWN_ITEMS + list(MARKET_ITEMS.keys())

# Items that show in TIN/KATHA column of PDF
KEEP_ITEMS_PDF = ['टिन', 'कथा', 'टिन / मसाला']

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'shop',
        shop_name TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        name TEXT NOT NULL,
        join_date TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS salary_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER NOT NULL,
        monthly_rate REAL NOT NULL,
        effective_from TEXT NOT NULL,
        FOREIGN KEY (staff_id) REFERENCES staff(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        present INTEGER NOT NULL DEFAULT 0,
        UNIQUE(staff_id, date)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS advances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        note TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS daily_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        date TEXT NOT NULL,
        cash_amount REAL DEFAULT 0,
        online_amount REAL DEFAULT 0,
        note TEXT,
        UNIQUE(shop_name, date)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity REAL DEFAULT 0,
        item_type TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(shop_name, item_name)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS restock_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        order_date TEXT NOT NULL,
        order_time TEXT,
        window_type TEXT DEFAULT "day",
        fulfilled INTEGER DEFAULT 0,
        fulfilled_date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        date TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity_used REAL NOT NULL,
        usage_date TEXT NOT NULL,
        UNIQUE(shop_name, item_name, usage_date)
    )''')

    # Sales categories with profit margins per shop
    c.execute('''CREATE TABLE IF NOT EXISTS shop_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        category_name TEXT NOT NULL,
        profit_percent REAL NOT NULL DEFAULT 20.0,
        is_active INTEGER DEFAULT 1,
        UNIQUE(shop_name, category_name)
    )''')

    # Daily sales now broken down by category
    c.execute('''CREATE TABLE IF NOT EXISTS daily_sales_by_category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        cash_amount REAL DEFAULT 0,
        online_amount REAL DEFAULT 0
    )''')

    # Sub-users (staff who can enter data but not see financials)
    c.execute('''CREATE TABLE IF NOT EXISTS sub_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        display_name TEXT NOT NULL,
        staff_id INTEGER,
        is_active INTEGER DEFAULT 1
    )''')

    # Seed admin user
    try:
        c.execute("INSERT INTO users (username, password, role, shop_name) VALUES (?,?,?,?)",
                  ("admin", "admin123", "admin", None))
    except:
        pass

    # Seed shop users
    for shop in SHOPS:
        try:
            uname = shop.lower().replace(" ", "_")
            c.execute("INSERT INTO users (username, password, role, shop_name) VALUES (?,?,?,?)",
                      (uname, uname + "123", "shop", shop))
        except:
            pass

    # Seed default categories for all shops
    DEFAULT_CATEGORIES = [
        ("पान (Paan)", 55.0),
        ("मार्केट आइटम (Market Items)", 18.0),
        ("घरेलू आइटम (Home Items)", 25.0),
    ]
    for shop in SHOPS:
        for cat_name, profit in DEFAULT_CATEGORIES:
            try:
                c.execute("INSERT INTO shop_categories (shop_name, category_name, profit_percent) VALUES (?,?,?)",
                          (shop, cat_name, profit))
            except:
                pass

    conn.commit()
    conn.close()

def authenticate(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, role, shop_name FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    if row:
        conn.close()
        return dict(row)
    c.execute("SELECT id, username, shop_name, display_name FROM sub_users WHERE username=? AND password=? AND is_active=1", (username, password))
    row = c.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["role"] = "subuser"
        return d
    return None

def get_sub_users(shop_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sub_users WHERE shop_name=? AND is_active=1", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_sub_user(shop_name, username, password, display_name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sub_users (shop_name, username, password, display_name) VALUES (?,?,?,?)",
                  (shop_name, username, password, display_name))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def get_shop_categories(shop_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM shop_categories WHERE shop_name=? AND is_active=1 ORDER BY category_name", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def upsert_category(shop_name, category_name, profit_percent, is_active=1):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO shop_categories (shop_name, category_name, profit_percent, is_active)
                 VALUES (?,?,?,?)
                 ON CONFLICT(shop_name, category_name) DO UPDATE SET
                 profit_percent=excluded.profit_percent, is_active=excluded.is_active""",
              (shop_name, category_name, profit_percent, is_active))
    conn.commit()
    conn.close()

def save_category_sales(shop_name, sale_date, category_sales):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM daily_sales_by_category WHERE shop_name=? AND date=?",
              (shop_name, str(sale_date)))
    for cat, amounts in category_sales.items():
        cash = amounts.get("cash", 0)
        online = amounts.get("online", 0)
        if cash > 0 or online > 0:
            c.execute("""INSERT INTO daily_sales_by_category (shop_name, date, category, cash_amount, online_amount)
                         VALUES (?,?,?,?,?)""", (shop_name, str(sale_date), cat, cash, online))
    conn.commit()
    conn.close()

def get_monthly_category_sales(shop_name, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT category, SUM(cash_amount) as cash, SUM(online_amount) as online,
                 SUM(cash_amount+online_amount) as total
                 FROM daily_sales_by_category
                 WHERE shop_name=? AND date LIKE ?
                 GROUP BY category""", (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ── Users (legacy stub) ──────────────────────────────────────────────
def _old_authenticate(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

# ── Staff ──────────────────────────────────────────────
def get_staff(shop_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT s.*, 
                 (SELECT monthly_rate FROM salary_rates WHERE staff_id=s.id ORDER BY effective_from DESC LIMIT 1) as current_rate
                 FROM staff s WHERE shop_name=? AND is_active=1""", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_all_staff():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT s.*, 
                 (SELECT monthly_rate FROM salary_rates WHERE staff_id=s.id ORDER BY effective_from DESC LIMIT 1) as current_rate
                 FROM staff s WHERE is_active=1""")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_staff(shop_name, name, join_date, monthly_rate):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO staff (shop_name, name, join_date) VALUES (?,?,?)",
              (shop_name, name, join_date))
    staff_id = c.lastrowid
    c.execute("INSERT INTO salary_rates (staff_id, monthly_rate, effective_from) VALUES (?,?,?)",
              (staff_id, monthly_rate, join_date))
    conn.commit()
    conn.close()
    return staff_id

def update_salary_rate(staff_id, new_rate, effective_from):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO salary_rates (staff_id, monthly_rate, effective_from) VALUES (?,?,?)",
              (staff_id, new_rate, effective_from))
    conn.commit()
    conn.close()

def add_advance(staff_id, amount, note=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO advances (staff_id, amount, date, note) VALUES (?,?,?,?)",
              (staff_id, amount, str(date.today()), note))
    conn.commit()
    conn.close()

def get_advances(staff_id, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM advances WHERE staff_id=? AND date LIKE ?",
              (staff_id, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ── Attendance ─────────────────────────────────────────
def mark_attendance(staff_id, att_date, present):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO attendance (staff_id, date, present) VALUES (?,?,?)",
              (staff_id, str(att_date), 1 if present else 0))
    conn.commit()
    conn.close()

def get_attendance(staff_id, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM attendance WHERE staff_id=? AND date LIKE ?",
              (staff_id, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_monthly_salary(staff_id, month, year):
    """Calculate salary: (rate / days_in_month) × days_present - advances"""
    import calendar
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"

    # Get rate effective for this month
    c.execute("""SELECT monthly_rate FROM salary_rates 
                 WHERE staff_id=? AND effective_from <= ? 
                 ORDER BY effective_from DESC LIMIT 1""",
              (staff_id, month_str + "-31"))
    rate_row = c.fetchone()
    rate = rate_row['monthly_rate'] if rate_row else 0

    # Days present
    c.execute("SELECT COUNT(*) as cnt FROM attendance WHERE staff_id=? AND date LIKE ? AND present=1",
              (staff_id, month_str + "%"))
    days_present = c.fetchone()['cnt']

    # Total advances this month
    c.execute("SELECT SUM(amount) as total FROM advances WHERE staff_id=? AND date LIKE ?",
              (staff_id, month_str + "%"))
    adv_row = c.fetchone()
    advances = adv_row['total'] or 0

    days_in_month = calendar.monthrange(year, month)[1]
    earned = (rate / days_in_month) * days_present if days_in_month > 0 else 0
    net = earned - advances

    conn.close()
    return {
        "rate": rate,
        "days_in_month": days_in_month,
        "days_present": days_present,
        "earned": round(earned, 2),
        "advances": round(advances, 2),
        "net_payable": round(net, 2)
    }

# ── Sales ──────────────────────────────────────────────
def save_daily_sales(shop_name, sale_date, cash, online, note=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO daily_sales (shop_name, date, cash_amount, online_amount, note)
                 VALUES (?,?,?,?,?)""", (shop_name, str(sale_date), cash, online, note))
    conn.commit()
    conn.close()

def get_monthly_sales(shop_name, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT * FROM daily_sales WHERE shop_name=? AND date LIKE ? ORDER BY date""",
              (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_all_shops_monthly_sales(month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT shop_name, SUM(cash_amount+online_amount) as total
                 FROM daily_sales WHERE date LIKE ? GROUP BY shop_name""", (month_str + "%",))
    rows = {r['shop_name']: r['total'] for r in c.fetchall()}
    conn.close()
    return rows

# ── Stock ──────────────────────────────────────────────
def get_stock(shop_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM stock WHERE shop_name=? ORDER BY item_type, item_name", (shop_name,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def update_stock(shop_name, item_name, quantity, item_type):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(shop_name, item_name) DO UPDATE SET
                 quantity=quantity+excluded.quantity, updated_at=excluded.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit()
    conn.close()

def set_initial_stock(shop_name, item_name, quantity, item_type):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""INSERT OR REPLACE INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (?,?,?,?,?)""", (shop_name, item_name, quantity, item_type, now))
    conn.commit()
    conn.close()

def get_all_stock():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM stock ORDER BY shop_name, item_type, item_name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ── Restock Orders ─────────────────────────────────────
def place_restock_order(shop_name, items_dict, window_type="day"):
    """items_dict: {item_name: quantity}"""
    conn = get_connection()
    c = conn.cursor()
    from datetime import datetime as dt
    now = dt.now().isoformat()
    today = str(date.today())
    for item, qty in items_dict.items():
        if qty and float(qty) > 0:
            c.execute("""INSERT INTO restock_orders (shop_name, item_name, quantity, order_date, order_time, window_type)
                         VALUES (?,?,?,?,?,?)""",
                      (shop_name, item, float(qty), today, now, window_type))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM restock_orders WHERE fulfilled=0 ORDER BY order_date DESC, shop_name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def fulfill_order(order_id, shop_name, item_name, quantity, item_type):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    # Mark fulfilled
    c.execute("UPDATE restock_orders SET fulfilled=1, fulfilled_date=? WHERE id=?",
              (now, order_id))
    # Update stock
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(shop_name, item_name) DO UPDATE SET
                 quantity=quantity+excluded.quantity, updated_at=excluded.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit()
    conn.close()

# ── Expenses ───────────────────────────────────────────
def add_expense(shop_name, amount, description, exp_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO expenses (shop_name, amount, description, date) VALUES (?,?,?,?)",
              (shop_name, amount, description, str(exp_date)))
    conn.commit()
    conn.close()

def get_monthly_expenses(shop_name, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("SELECT * FROM expenses WHERE shop_name=? AND date LIKE ? ORDER BY date",
              (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ── Order Time Window ──────────────────────────────────
def is_order_window_open():
    """Returns (is_open, window_type) where window_type is 'day', 'night', or None"""
    from datetime import datetime
    now = datetime.now()
    current = now.hour * 60 + now.minute
    day_start   = 10 * 60       # 10:00
    day_end     = 18 * 60 + 40  # 18:40
    night_start = 0             # 00:00
    night_end   = 4 * 60        # 04:00
    if day_start <= current <= day_end:
        return (True, "day")
    if night_start <= current <= night_end:
        return (True, "night")
    return (False, None)

def next_window_time():
    from datetime import datetime
    now = datetime.now()
    h = now.hour
    if 4 < h < 10:
        return "10:00 AM"
    if h > 18:
        return "12:00 AM (midnight)"
    return "10:00 AM"

# ── User Management ────────────────────────────────────
def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='shop' ORDER BY shop_name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def update_user_password(username, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
    conn.commit()
    conn.close()

def get_pending_orders_filtered(date_from=None, date_to=None, window_type=None, merge_duplicates=True):
    """Get pending orders with optional filters. Merge duplicates by default."""
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM restock_orders WHERE fulfilled=0"
    params = []
    if date_from:
        query += " AND order_date >= ?"
        params.append(str(date_from))
    if date_to:
        query += " AND order_date <= ?"
        params.append(str(date_to))
    if window_type:
        query += " AND window_type=?"
        params.append(window_type)
    query += " ORDER BY order_date DESC, shop_name"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if not merge_duplicates:
        return rows

    # Merge duplicates: same shop + same item → sum quantities, keep latest id
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

def fulfill_orders_bulk(ids, shop_name, item_name, quantity, item_type):
    """Fulfill multiple order IDs at once (for merged duplicates)"""
    conn = get_connection()
    c = conn.cursor()
    from datetime import datetime as dt
    now = dt.now().isoformat()
    for oid in ids:
        c.execute("UPDATE restock_orders SET fulfilled=1, fulfilled_date=? WHERE id=?", (now, oid))
    # Update stock once with total quantity
    c.execute("""INSERT INTO stock (shop_name, item_name, quantity, item_type, updated_at)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(shop_name, item_name) DO UPDATE SET
                 quantity=quantity+excluded.quantity, updated_at=excluded.updated_at""",
              (shop_name, item_name, quantity, item_type, now))
    conn.commit()
    conn.close()

def link_subuser_to_staff(username, staff_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sub_users SET staff_id=? WHERE username=?", (staff_id, username))
    conn.commit()
    conn.close()

# ── Supply Tracking (Admin) ────────────────────────────
# Admin records what they supplied to each shop per category
# with cost and profit % → calculates expected vs actual revenue

SUPPLY_CATEGORIES = [
    ("Godown / Home (Sweets)", 55.0),
    ("Market Items",           18.0),
    ("Paan",                   50.0),
    ("Cigarettes",             12.0),
    ("Other",                  20.0),
]

def init_supply_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS supply_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL,
        supply_date TEXT NOT NULL,
        category TEXT NOT NULL,
        cost_amount REAL NOT NULL,
        profit_percent REAL NOT NULL,
        expected_revenue REAL NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS category_profit_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        profit_percent REAL NOT NULL DEFAULT 20.0
    )''')
    # Seed default profit %
    for cat, pct in SUPPLY_CATEGORIES:
        try:
            c.execute("INSERT INTO category_profit_settings (category, profit_percent) VALUES (?,?)", (cat, pct))
        except:
            pass
    conn.commit()
    conn.close()

def get_profit_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM category_profit_settings ORDER BY category")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def update_profit_setting(category, profit_percent):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO category_profit_settings (category, profit_percent) VALUES (?,?)
                 ON CONFLICT(category) DO UPDATE SET profit_percent=excluded.profit_percent""",
              (category, profit_percent))
    conn.commit()
    conn.close()

def add_supply(shop_name, supply_date, category, cost_amount, profit_percent, note=""):
    expected = cost_amount * (1 + profit_percent / 100)
    conn = get_connection()
    c = conn.cursor()
    from datetime import datetime as dt
    c.execute("""INSERT INTO supply_log (shop_name, supply_date, category, cost_amount,
                 profit_percent, expected_revenue, note, created_at)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (shop_name, str(supply_date), category, cost_amount,
               profit_percent, round(expected, 2), note, dt.now().isoformat()))
    conn.commit()
    conn.close()

def get_monthly_supply(shop_name, month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT * FROM supply_log WHERE shop_name=? AND supply_date LIKE ?
                 ORDER BY supply_date, category""",
              (shop_name, month_str + "%"))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_all_shops_monthly_supply(month, year):
    conn = get_connection()
    c = conn.cursor()
    month_str = f"{year}-{month:02d}"
    c.execute("""SELECT shop_name,
                 SUM(cost_amount) as total_cost,
                 SUM(expected_revenue) as total_expected
                 FROM supply_log WHERE supply_date LIKE ?
                 GROUP BY shop_name""", (month_str + "%",))
    rows = {r['shop_name']: dict(r) for r in c.fetchall()}
    conn.close()
    return rows

def delete_supply(supply_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM supply_log WHERE id=?", (supply_id,))
    conn.commit()
    conn.close()

# ── Daily Usage ────────────────────────────────────────
def save_daily_usage(shop_name, usage_date, usage_dict):
    """usage_dict: {item_name: quantity_used}"""
    conn = get_connection()
    c = conn.cursor()
    for item, qty in usage_dict.items():
        if qty and float(qty) > 0:
            c.execute("""INSERT OR REPLACE INTO daily_usage
                         (shop_name, item_name, quantity_used, usage_date)
                         VALUES (?,?,?,?)""",
                      (shop_name, item, float(qty), str(usage_date)))
    conn.commit()
    conn.close()

def get_usage_since(shop_name, since_date):
    """Total usage per item since a given date"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT item_name, SUM(quantity_used) as total_used
                 FROM daily_usage WHERE shop_name=? AND usage_date >= ?
                 GROUP BY item_name""", (shop_name, str(since_date)))
    rows = {r['item_name']: r['total_used'] for r in c.fetchall()}
    conn.close()
    return rows

def get_approx_stock(shop_name):
    """
    Returns list of {item, stocked_qty, used_qty, approx_remaining, last_restock_date, status}
    status: 'good' | 'low' | 'out'
    """
    from datetime import datetime, timedelta
    conn = get_connection()
    c = conn.cursor()

    # Get current stock (set manually or via restock fulfillment)
    c.execute("SELECT item_name, quantity, updated_at FROM stock WHERE shop_name=?", (shop_name,))
    stock_rows = {r['item_name']: dict(r) for r in c.fetchall()}

    # Get last restock date per item
    c.execute("""SELECT item_name, MAX(fulfilled_date) as last_date, SUM(quantity) as restocked
                 FROM restock_orders WHERE shop_name=? AND fulfilled=1
                 GROUP BY item_name""", (shop_name,))
    restock_rows = {r['item_name']: dict(r) for r in c.fetchall()}
    conn.close()

    results = []
    for item, stock in stock_rows.items():
        # Get usage since last restock
        last_restock = restock_rows.get(item, {}).get('last_date')
        if last_restock:
            since = last_restock[:10]  # date part only
        else:
            # Use stock updated_at as baseline
            since = (stock.get('updated_at') or '')[:10] or '2024-01-01'

        usage = get_usage_since(shop_name, since)
        used = usage.get(item, 0)
        stocked = stock['quantity']
        remaining = max(stocked - used, 0)

        # Status
        if stocked == 0:
            status = 'unknown'
        elif remaining <= 0:
            status = 'out'
        elif remaining < stocked * 0.2:
            status = 'low'
        elif remaining < stocked * 0.5:
            status = 'medium'
        else:
            status = 'good'

        results.append({
            'item': item,
            'stocked': stocked,
            'used': used,
            'remaining': remaining,
            'last_restock': last_restock,
            'status': status,
        })

    return sorted(results, key=lambda x: x['status'])

def get_all_shops_stock_status():
    """Quick status per shop — for dashboard tiles"""
    results = {}
    for shop in SHOPS:
        stock = get_approx_stock(shop)
        if not stock:
            results[shop] = 'no_data'
            continue
        out  = sum(1 for s in stock if s['status'] == 'out')
        low  = sum(1 for s in stock if s['status'] == 'low')
        if out > 0:
            results[shop] = 'out'
        elif low > 0:
            results[shop] = 'low'
        else:
            results[shop] = 'good'
    return results

# ── Item Management ────────────────────────────────────
def init_item_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS custom_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        price REAL DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        added_at TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def get_all_items_managed():
    """Returns all items (built-in + custom) with active status"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM custom_items ORDER BY category, item_name")
    custom = [dict(r) for r in c.fetchall()]
    conn.close()
    return custom

def add_custom_item(item_name, category, price=0):
    from datetime import datetime as dt
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO custom_items (item_name, category, price, is_active, added_at) VALUES (?,?,?,1,?)",
                  (item_name.strip(), category, price, dt.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def toggle_item_active(item_name, active):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE custom_items SET is_active=? WHERE item_name=?", (1 if active else 0, item_name))
    conn.commit()
    conn.close()

def get_active_items_by_category():
    """Returns merged built-in + custom active items per category"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT item_name, category, price FROM custom_items WHERE is_active=1")
    custom = [dict(r) for r in c.fetchall()]
    conn.close()

    # Start with built-ins
    result = {
        'godown':     list(GODOWN_ITEMS),
        'paan':       list(PAAN_ITEMS),
        'market':     list(MARKET_ITEMS.keys()),
        'morning':    ['टिन', 'टिन / मसाला', 'पार्सल कवर', 'कथा'],
    }
    prices = dict(MARKET_ITEMS)

    # Add custom items
    for item in custom:
        cat = item['category']
        if cat in result and item['item_name'] not in result[cat]:
            result[cat].append(item['item_name'])
        if item['price'] > 0:
            prices[item['item_name']] = item['price']

    return result, prices

# ── Admin User Management ──────────────────────────────
def get_admin_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='admin' ORDER BY username")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_admin_user(username, password, display_name=""):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, shop_name) VALUES (?,?,?,?)",
                  (username.strip(), password, 'admin', display_name or None))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def deactivate_user(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE username=?", ("__DISABLED__", username))
    conn.commit()
    conn.close()
