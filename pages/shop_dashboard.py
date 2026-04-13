import streamlit as st
from datetime import date, datetime
import calendar
from database import (
    save_daily_sales, get_monthly_sales,
    get_stock, set_initial_stock,
    place_restock_order, add_expense, get_monthly_expenses,
    mark_attendance, get_attendance,
    get_monthly_salary, get_staff,
    is_order_window_open, next_window_time,
    save_daily_usage, get_approx_stock,
    PAAN_ITEMS, GODOWN_ITEMS, LOCAL_ITEMS, MARKET_ITEMS, ALL_ITEMS
)

def show():
    if not st.session_state.get("user"):
        st.error("🔒 Access denied.")
        st.stop()

    shop = st.session_state.shop_name
    role = st.session_state.role

    st.sidebar.markdown(f"### 🌿 {shop}")
    st.sidebar.markdown(f"*{'Sub User' if role == 'subuser' else 'Shop Portal'}*")

    menu = [
        "📊 Dashboard",
        "💰 Daily Sales / रोज़ की बिक्री",
        "📦 My Stock / मेरा स्टॉक",
        "🔄 Order Restock / ऑर्डर",
        "💸 Expenses / खर्च",
        "📉 Daily Usage / रोज़ का उपयोग",
    ]
    if role == "subuser":
        menu.append("📅 My Attendance / हाज़िरी")

    page = st.sidebar.radio("Menu / मेनू", menu)

    if st.sidebar.button("🚪 Logout"):
        for k in ["user","role","shop_name"]:
            st.session_state[k] = None
        st.rerun()

    today = date.today()

    if page == "📊 Dashboard":
        show_dashboard(shop, today)
    elif page == "💰 Daily Sales / रोज़ की बिक्री":
        show_sales(shop, today)
    elif page == "📦 My Stock / मेरा स्टॉक":
        show_stock(shop)
    elif page == "🔄 Order Restock / ऑर्डर":
        show_restock(shop, today)
    elif page == "💸 Expenses / खर्च":
        show_expenses(shop, today)
    elif page == "📉 Daily Usage / रोज़ का उपयोग":
        show_usage(shop, today)
    elif page == "📅 My Attendance / हाज़िरी":
        show_my_attendance(shop, today)


def show_dashboard(shop, today):
    st.title(f"📊 {shop}")
    m, y = today.month, today.year
    pm = m - 1 if m > 1 else 12
    py = y if m > 1 else y - 1

    sales = get_monthly_sales(shop, m, y)
    prev_sales = get_monthly_sales(shop, pm, py)
    total = sum(s['cash_amount'] + s['online_amount'] for s in sales)
    prev_total = sum(s['cash_amount'] + s['online_amount'] for s in prev_sales)
    expenses = get_monthly_expenses(shop, m, y)
    total_exp = sum(e['amount'] for e in expenses)

    col1, col2, col3 = st.columns(3)
    col1.metric("This Month Sales", f"Rs {total:,.0f}",
                delta=f"Rs {total - prev_total:,.0f} vs last month")
    col2.metric("Expenses", f"Rs {total_exp:,.0f}")
    col3.metric("Net", f"Rs {total - total_exp:,.0f}")

    st.divider()
    st.subheader("Current Stock")
    stock = get_stock(shop)
    if stock:
        local = [(s['item_name'], s['quantity']) for s in stock if s['item_type'] == 'local']
        market = [(s['item_name'], s['quantity']) for s in stock if s['item_type'] == 'market']
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Local Items**")
            for name, qty in local:
                st.write(f"• {name}: **{qty}**")
        with c2:
            st.write("**Market Items**")
            for name, qty in market:
                st.write(f"• {name}: **{qty}**")
    else:
        st.info("No stock data yet.")


def show_sales(shop, today):
    st.title("💰 Daily Sales / रोज़ की बिक्री")

    with st.form("sales_form"):
        sale_date = st.date_input("Date / तारीख", value=today)
        c1, c2 = st.columns(2)
        with c1:
            cash = st.number_input("Cash / नकद (Rs)", min_value=0.0, step=10.0)
        with c2:
            online = st.number_input("Online / ऑनलाइन (Rs)", min_value=0.0, step=10.0)
        note = st.text_input("Note (optional)")
        if st.form_submit_button("Save / सेव करें", use_container_width=True):
            save_daily_sales(shop, sale_date, cash, online, note)
            st.success(f"✅ Saved! Total: Rs {cash + online:,.0f}")

    st.divider()
    st.subheader("Monthly Sales")
    c1, c2 = st.columns(2)
    with c1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    sales = get_monthly_sales(shop, sel_month, sel_year)
    if sales:
        import pandas as pd
        df = pd.DataFrame(sales)[['date','cash_amount','online_amount','note']]
        df['Total'] = df['cash_amount'] + df['online_amount']
        df.columns = ['Date','Cash','Online','Note','Total']
        st.dataframe(df, use_container_width=True)
        st.metric("Month Total", f"Rs {df['Total'].sum():,.0f}")
    else:
        st.info("No sales this month.")


def show_stock(shop):
    st.title("📦 My Stock / मेरा स्टॉक")
    stock = get_stock(shop)
    tab1, tab2 = st.tabs(["View / देखें", "Set Initial Stock"])

    with tab1:
        if stock:
            import pandas as pd
            df = pd.DataFrame(stock)[['item_name','item_type','quantity','updated_at']]
            df.columns = ['Item','Type','Qty','Updated']
            df['Type'] = df['Type'].map({'local':'🟢 Local','market':'🔵 Market'})
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No stock set yet.")

    with tab2:
        stock_dict = {s['item_name']: s for s in stock}
        with st.form("stock_form"):
            st.write("**Local Items**")
            local_vals = {}
            cols = st.columns(3)
            for i, item in enumerate(LOCAL_ITEMS):
                with cols[i%3]:
                    curr = stock_dict.get(item,{}).get('quantity',0)
                    local_vals[item] = st.number_input(item, min_value=0.0, value=float(curr), step=1.0, key=f"ls_{item}")
            st.write("**Market Items**")
            market_vals = {}
            cols2 = st.columns(3)
            for i, item in enumerate(MARKET_ITEMS.keys()):
                with cols2[i%3]:
                    curr = stock_dict.get(item,{}).get('quantity',0)
                    market_vals[item] = st.number_input(item, min_value=0.0, value=float(curr), step=1.0, key=f"ms_{item}")
            if st.form_submit_button("Save Stock", use_container_width=True):
                for item, qty in {**local_vals, **market_vals}.items():
                    if qty > 0:
                        itype = 'local' if item in LOCAL_ITEMS else 'market'
                        set_initial_stock(shop, item, qty, itype)
                st.success("✅ Stock updated!")
                st.rerun()


def show_restock(shop, today):
    st.title("🔄 Order Restock / रीस्टॉक ऑर्डर")

    window_open, window_type = is_order_window_open()
    if not window_open:
        st.error(f"🕐 Order window closed. Next window: **{next_window_time()}**")
        st.info("Windows: 10:00 AM – 6:40 PM  |  12:00 AM – 4:00 AM")
        return

    if window_type == "night":
        st.warning("🌙 Night window (12am–4am) — small refills only")
    else:
        st.success("✅ Order window open until 6:40 PM")

    with st.form("restock_form"):
        st.write("**Local Items / लोकल आइटम**")
        local_order = {}
        cols = st.columns(3)
        for i, item in enumerate(LOCAL_ITEMS):
            with cols[i%3]:
                local_order[item] = st.number_input(item, min_value=0.0, step=1.0, key=f"ro_l_{item}")
        st.write("**Market Items / मार्केट आइटम**")
        market_order = {}
        cols2 = st.columns(3)
        for i, item in enumerate(MARKET_ITEMS.keys()):
            with cols2[i%3]:
                market_order[item] = st.number_input(item, min_value=0.0, step=1.0, key=f"ro_m_{item}")
        extra = st.text_area("Extra / अतिरिक्त आइटम (type anything)", height=80, key="extra_items")
        if st.form_submit_button("📤 Place Order / ऑर्डर दें", use_container_width=True):
            all_orders = {k: v for k, v in {**local_order, **market_order}.items() if v > 0}
            if all_orders:
                place_restock_order(shop, all_orders, window_type, extra_note=extra)
                st.success(f"✅ Order placed for {len(all_orders)} items!")
            else:
                st.warning("Enter at least one item.")


def show_expenses(shop, today):
    st.title("💸 Expenses / खर्च")

    with st.form("exp_form"):
        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input("Amount (Rs)", min_value=0.0, step=10.0)
        with c2:
            exp_date = st.date_input("Date", value=today)
        desc = st.text_input("Description (e.g. house rent, online sent)")
        if st.form_submit_button("Add Expense", use_container_width=True):
            if amount > 0:
                add_expense(shop, amount, desc, exp_date)
                st.success("✅ Added!")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    expenses = get_monthly_expenses(shop, sel_month, sel_year)
    if expenses:
        import pandas as pd
        df = pd.DataFrame(expenses)[['date','description','amount']]
        df.columns = ['Date','Description','Amount Rs']
        st.dataframe(df, use_container_width=True)
        st.metric("Total", f"Rs {df['Amount Rs'].sum():,.0f}")
    else:
        st.info("No expenses this month.")


def show_my_attendance(shop, today):
    st.title("📅 My Attendance / मेरी हाज़िरी")
    username = st.session_state.user

    from database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT staff_id FROM sub_users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        st.info("No salary profile linked. Ask admin to link your account to a staff record.")
        return

    staff_id = row[0] if isinstance(row, tuple) else row['staff_id']

    att_date = st.date_input("Mark for date", value=today)
    existing = get_attendance(staff_id, att_date.month, att_date.year)
    day_rec = next((a for a in existing if a['date'] == str(att_date)), None)
    current = bool(day_rec['present']) if day_rec else False

    present = st.checkbox("Present today / आज उपस्थित", value=current)
    if present != current:
        mark_attendance(staff_id, att_date, present)
        st.success("✅ Marked!")
        st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    att = get_attendance(staff_id, sel_month, sel_year)
    days_present = sum(1 for a in att if a['present'])
    days_in_month = calendar.monthrange(sel_year, sel_month)[1]
    st.metric("Days Present", f"{days_present} / {days_in_month}")
    sal = get_monthly_salary(staff_id, sel_month, sel_year)
    st.metric("Estimated Salary", f"Rs {sal['earned']:,.0f}")
    if sal['advances'] > 0:
        st.metric("Advance Taken", f"Rs {sal['advances']:,.0f}")
        st.metric("Net Payable", f"Rs {sal['net_payable']:,.0f}")


def show_usage(shop, today):
    st.title("📉 Daily Usage / रोज़ का उपयोग")
    st.caption("Before leaving — enter how much of each item you used today")

    stock = get_stock(shop)
    stock_dict = {s['item_name']: s['quantity'] for s in stock}

    if not stock_dict:
        st.warning("Set your initial stock first in 📦 My Stock.")
        return

    with st.form("usage_form"):
        usage_date = st.date_input("Date / तारीख", value=today)

        st.write("**पान आइटम / Paan Items**")
        usage = {}
        paan_in_stock = [(item, stock_dict[item]) for item in PAAN_ITEMS if item in stock_dict]
        if paan_in_stock:
            cols = st.columns(3)
            for i, (item, curr) in enumerate(paan_in_stock):
                with cols[i%3]:
                    usage[item] = st.number_input(
                        f"{item} (have {curr:.0f})",
                        min_value=0.0, max_value=float(curr), step=1.0, key=f"u_p_{item}")
        else:
            st.caption("No paan items in stock")

        st.write("**गोदाम आइटम / Godown Items**")
        godown_in_stock = [(item, stock_dict[item]) for item in GODOWN_ITEMS if item in stock_dict]
        if godown_in_stock:
            cols2 = st.columns(3)
            for i, (item, curr) in enumerate(godown_in_stock):
                with cols2[i%3]:
                    usage[item] = st.number_input(
                        f"{item} (have {curr:.0f})",
                        min_value=0.0, max_value=float(curr), step=1.0, key=f"u_g_{item}")

        st.write("**मार्केट आइटम / Market Items**")
        mkt_in_stock = [(item, stock_dict[item]) for item in MARKET_ITEMS.keys() if item in stock_dict]
        if mkt_in_stock:
            cols3 = st.columns(3)
            for i, (item, curr) in enumerate(mkt_in_stock):
                with cols3[i%3]:
                    usage[item] = st.number_input(
                        f"{item} (have {curr:.0f})",
                        min_value=0.0, max_value=float(curr), step=1.0, key=f"u_m_{item}")

        if st.form_submit_button("💾 Save Usage / सेव करें", use_container_width=True):
            non_zero = {k: v for k, v in usage.items() if v > 0}
            if non_zero:
                save_daily_usage(shop, usage_date, non_zero)
                st.success(f"✅ Usage saved for {len(non_zero)} items!")
            else:
                st.warning("Enter at least one item usage.")

    st.divider()
    st.subheader("Approx Current Stock / अनुमानित स्टॉक")
    approx = get_approx_stock(shop)
    if approx:
        for s in approx:
            icon = "🟢" if s['status']=='good' else ("🟡" if s['status']=='medium' else ("🔴" if s['status']=='out' else "⚪"))
            st.write(f"{icon} **{s['item']}** — ~{s['remaining']:.0f} remaining (used {s['used']:.0f} of {s['stocked']:.0f})")
    else:
        st.info("Set initial stock to see estimates.")
