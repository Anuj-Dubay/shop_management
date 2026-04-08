import streamlit as st
from datetime import date, datetime
import calendar

    
from database import (
    get_staff, add_staff, mark_attendance, get_attendance, get_monthly_salary,
    add_advance, get_advances, save_daily_sales, get_monthly_sales,
    get_stock, update_stock, set_initial_stock, place_restock_order,
    add_expense, get_monthly_expenses, update_salary_rate,
    get_shop_categories, upsert_category, save_category_sales, get_monthly_category_sales,
    get_sub_users, add_sub_user,
    LOCAL_ITEMS, MARKET_ITEMS, ALL_ITEMS
)

def show():
    if not st.session_state.get("user"):
        st.error("🔒 Access denied. Please login via the main app.")
        st.stop()
    
    shop = st.session_state.shop_name

    st.sidebar.markdown(f"### 🌿 {shop}")
    st.sidebar.markdown(f"*Shop Portal*")

    is_subuser = st.session_state.role == "subuser"
    menu_options = [
        "📊 Dashboard",
        "💰 Daily Sales / रोज़ की बिक्री",
        "📦 My Stock / मेरा स्टॉक",
        "🔄 Order Restock / ऑर्डर",
        "📅 Attendance / हाज़िरी",
    ]
    if not is_subuser:
        menu_options += ["👷 Staff & Salary / स्टाफ", "⚙️ Shop Settings"]
    page = st.sidebar.radio("Menu / मेनू", menu_options)

    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.shop_name = None
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
    elif page == "📅 Attendance / हाज़िरी":
        show_attendance(shop, today)
    elif page == "👷 Staff & Salary / स्टाफ":
        show_staff(shop, today)
    elif page == "⚙️ Shop Settings":
        show_settings(shop)


def show_dashboard(shop, today):
    st.title(f"📊 {shop} — Dashboard")

    col1, col2 = st.columns(2)
    m, y = today.month, today.year

    with col1:
        st.subheader("This Month Sales / इस महीने की बिक्री")
        sales = get_monthly_sales(shop, m, y)
        total_cash = sum(s['cash_amount'] for s in sales)
        total_online = sum(s['online_amount'] for s in sales)
        total = total_cash + total_online
        st.metric("Total / कुल", f"₹{total:,.0f}")
        st.metric("Cash / नकद", f"₹{total_cash:,.0f}")
        st.metric("Online / ऑनलाइन", f"₹{total_online:,.0f}")

    with col2:
        st.subheader("Previous Month / पिछला महीने")
        pm = m - 1 if m > 1 else 12
        py = y if m > 1 else y - 1
        prev_sales = get_monthly_sales(shop, pm, py)
        prev_total = sum(s['cash_amount'] + s['online_amount'] for s in prev_sales)
        st.metric("Total / कुल", f"₹{prev_total:,.0f}",
                  delta=f"₹{total - prev_total:,.0f} vs last month")

    st.divider()

    st.subheader("Current Stock Summary / स्टॉक सारांश")
    stock = get_stock(shop)
    if stock:
        local = [(s['item_name'], s['quantity']) for s in stock if s['item_type'] == 'local']
        market = [(s['item_name'], s['quantity']) for s in stock if s['item_type'] == 'market']

        c1, c2 = st.columns(2)
        with c1:
            st.write("**Local Items / लोकल आइटम**")
            for name, qty in local:
                st.write(f"• {name}: **{qty}**")
        with c2:
            st.write("**Market Items / मार्केट आइटम**")
            for name, qty in market:
                st.write(f"• {name}: **{qty}**")
    else:
        st.info("No stock entered yet. Go to 'My Stock' to set initial stock.")


def show_sales(shop, today):
    st.title("💰 Daily Sales Entry / रोज़ की बिक्री")

    categories = get_shop_categories(shop)
    if not categories:
        st.warning("No categories set. Go to ⚙️ Shop Settings to configure.")
        return

    with st.form("sales_form"):
        sale_date = st.date_input("Date / तारीख", value=today)
        st.write("**Enter sales per category:**")
        cat_inputs = {}
        for cat in categories:
            cname = cat['category_name']
            st.write(f"**{cname}** *(profit: {cat['profit_percent']}%)*")
            c1, c2 = st.columns(2)
            with c1:
                cash = st.number_input(f"Cash ₹", min_value=0.0, step=10.0, key=f"cash_{cname}")
            with c2:
                online = st.number_input(f"Online ₹", min_value=0.0, step=10.0, key=f"online_{cname}")
            cat_inputs[cname] = {"cash": cash, "online": online}
            st.divider()

        note = st.text_input("Note / नोट (optional)")
        submitted = st.form_submit_button("Save / सेव करें", use_container_width=True)

        if submitted:
            save_category_sales(shop, sale_date, cat_inputs)
            total = sum(v["cash"] + v["online"] for v in cat_inputs.values())
            st.success(f"✅ Saved! Total: ₹{total:,.0f}")

    st.divider()
    st.subheader("Monthly Breakdown / महीने की बिक्री")
    col1, col2 = st.columns(2)
    with col1:
        sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                                  format_func=lambda m: datetime(2000, m, 1).strftime("%B"))
    with col2:
        sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1)

    cat_sales = get_monthly_category_sales(shop, sel_month, sel_year)
    if cat_sales:
        import pandas as pd
        cat_map = {c['category_name']: c['profit_percent'] for c in categories}
        rows = []
        for cs in cat_sales:
            profit_pct = cat_map.get(cs['category'], 20.0)
            profit_amt = cs['total'] * profit_pct / 100
            rows.append({
                'Category': cs['category'],
                'Cash ₹': cs['cash'],
                'Online ₹': cs['online'],
                'Total ₹': cs['total'],
                'Profit % ': f"{profit_pct}%",
                'Est. Profit ₹': round(profit_amt, 0)
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        total_sales = df['Total ₹'].sum()
        total_profit = df['Est. Profit ₹'].sum()
        m1, m2 = st.columns(2)
        m1.metric("Total Sales", f"₹{total_sales:,.0f}")
        m2.metric("Est. Profit", f"₹{total_profit:,.0f}")
    else:
        st.info("No sales recorded for this month.")

    st.divider()
    st.subheader("Add Expense / खर्च दर्ज करें")
    with st.form("expense_form"):
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            exp_amount = st.number_input("Amount / राशि (₹)", min_value=0.0, step=10.0)
        with exp_col2:
            exp_date = st.date_input("Expense Date", value=today, key="exp_date")
        exp_desc = st.text_input("Description / विवरण")
        exp_submitted = st.form_submit_button("Add Expense / खर्च जोड़ें")
        if exp_submitted and exp_amount > 0:
            add_expense(shop, exp_amount, exp_desc, exp_date)
            st.success("✅ Expense added!")


def show_settings(shop):
    st.title("⚙️ Shop Settings / दुकान सेटिंग")

    tab1, tab2 = st.tabs(["Categories / श्रेणियाँ", "Sub Users / सब यूज़र"])

    with tab1:
        st.subheader("Sales Categories & Profit %")
        st.info("Set which categories your shop sells, and the estimated profit % for each.")

        categories = get_shop_categories(shop)
        cat_dict = {c['category_name']: c for c in categories}

        AVAILABLE_CATS = [
            ("पान (Paan)", 55.0),
            ("मार्केट आइटम (Market Items)", 18.0),
            ("घरेलू आइटम (Home Items)", 25.0),
            ("सिगरेट (Cigarettes)", 12.0),
            ("कोल्ड ड्रिंक (Cold Drinks)", 20.0),
            ("अन्य (Other)", 20.0),
        ]

        with st.form("cat_form"):
            for cat_name, default_pct in AVAILABLE_CATS:
                existing = cat_dict.get(cat_name)
                curr_pct = existing['profit_percent'] if existing else default_pct
                curr_active = bool(existing['is_active']) if existing else False

                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{cat_name}**")
                with col2:
                    pct = st.number_input(f"Profit %", min_value=0.0, max_value=100.0,
                                          value=curr_pct, step=1.0, key=f"pct_{cat_name}")
                with col3:
                    active = st.checkbox("Active", value=curr_active, key=f"act_{cat_name}")

            if st.form_submit_button("Save Categories", use_container_width=True):
                for cat_name, _ in AVAILABLE_CATS:
                    pct_key = f"pct_{cat_name}"
                    act_key = f"act_{cat_name}"
                    # Read from session_state since form already submitted
                    upsert_category(shop, cat_name,
                                    st.session_state.get(pct_key, 20.0),
                                    1 if st.session_state.get(act_key, False) else 0)
                st.success("✅ Categories saved!")
                st.rerun()

    with tab2:
        st.subheader("Sub Users / सब यूज़र")
        st.info("Sub users can enter daily sales and attendance, but cannot see salary or financials.")

        sub_users = get_sub_users(shop)
        if sub_users:
            for su in sub_users:
                st.write(f"👤 **{su['display_name']}** — login: `{su['username']}`")
        else:
            st.write("No sub users yet.")

        st.divider()
        with st.form("add_sub_user_form"):
            st.write("**Add Sub User**")
            su_name = st.text_input("Display Name (e.g. Raju)")
            su_user = st.text_input("Username (for login)")
            su_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Add Sub User"):
                if su_name and su_user and su_pass:
                    ok = add_sub_user(shop, su_user, su_pass, su_name)
                    if ok:
                        st.success(f"✅ {su_name} added! They can login with: {su_user}")
                    else:
                        st.error("Username already taken, try another.")
                else:
                    st.error("All fields required.")


def show_stock(shop):
    st.title("📦 My Stock / मेरा स्टॉक")

    stock = get_stock(shop)
    stock_dict = {s['item_name']: s for s in stock}

    tab1, tab2 = st.tabs(["View Stock / स्टॉक देखें", "Set Initial Stock / शुरुआती स्टॉक"])

    with tab1:
        if stock:
            import pandas as pd
            df = pd.DataFrame(stock)[['item_name', 'item_type', 'quantity', 'updated_at']]
            df.columns = ['Item / आइटम', 'Type', 'Qty', 'Last Updated']
            df['Type'] = df['Type'].map({'local': '🟢 Local', 'market': '🔵 Market'})
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No stock set yet. Use 'Set Initial Stock' tab below.")

    with tab2:
        st.write("Enter current quantities for each item:")
        with st.form("initial_stock_form"):
            st.write("**Local Items / लोकल आइटम**")
            local_vals = {}
            cols = st.columns(3)
            for i, item in enumerate(LOCAL_ITEMS):
                with cols[i % 3]:
                    curr = stock_dict.get(item, {}).get('quantity', 0)
                    local_vals[item] = st.number_input(item, min_value=0.0, value=float(curr), step=1.0, key=f"ls_{item}")

            st.write("**Market Items / मार्केट आइटम**")
            market_vals = {}
            cols2 = st.columns(3)
            for i, item in enumerate(MARKET_ITEMS.keys()):
                with cols2[i % 3]:
                    curr = stock_dict.get(item, {}).get('quantity', 0)
                    market_vals[item] = st.number_input(item, min_value=0.0, value=float(curr), step=1.0, key=f"ms_{item}")

            if st.form_submit_button("Save Stock / स्टॉक सेव करें", use_container_width=True):
                for item, qty in local_vals.items():
                    if qty > 0:
                        set_initial_stock(shop, item, qty, 'local')
                for item, qty in market_vals.items():
                    if qty > 0:
                        set_initial_stock(shop, item, qty, 'market')
                st.success("✅ Stock updated!")
                st.rerun()


def show_restock(shop, today):
    st.title("🔄 Order Restock / रीस्टॉक ऑर्डर")
    st.info("Enter quantities you need. Admin will fulfill and stock will update automatically.")

    with st.form("restock_form"):
        st.write("**Local Items / लोकल आइटम**")
        local_order = {}
        cols = st.columns(3)
        for i, item in enumerate(LOCAL_ITEMS):
            with cols[i % 3]:
                local_order[item] = st.number_input(item, min_value=0.0, step=1.0, key=f"ro_l_{item}")

        st.write("**Market Items / मार्केट आइटम**")
        market_order = {}
        cols2 = st.columns(3)
        for i, item in enumerate(MARKET_ITEMS.keys()):
            with cols2[i % 3]:
                market_order[item] = st.number_input(item, min_value=0.0, step=1.0, key=f"ro_m_{item}")

        if st.form_submit_button("📤 Place Order / ऑर्डर दें", use_container_width=True):
            all_orders = {**local_order, **market_order}
            non_zero = {k: v for k, v in all_orders.items() if v > 0}
            if non_zero:
                place_restock_order(shop, non_zero)
                st.success(f"✅ Order placed for {len(non_zero)} items!")
            else:
                st.warning("Please enter at least one item quantity.")


def show_staff(shop, today):
    st.title("👷 Staff & Salary / स्टाफ और वेतन")

    tab1, tab2, tab3 = st.tabs(["Staff List / सूची", "Add Staff / जोड़ें", "Salary Report / वेतन"])

    with tab1:
        staff = get_staff(shop)
        if staff:
            for s in staff:
                with st.expander(f"👤 {s['name']} — ₹{s['current_rate'] or 0:,.0f}/month"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Joined:** {s['join_date']}")
                        st.write(f"**Rate:** ₹{s['current_rate'] or 0:,.0f}/month")
                    with col2:
                        new_rate = st.number_input("New Rate / नई दर", min_value=0.0,
                                                    value=float(s['current_rate'] or 0),
                                                    key=f"rate_{s['id']}")
                        eff_date = st.date_input("Effective From", value=today, key=f"eff_{s['id']}")
                        if st.button("Update Rate", key=f"upd_{s['id']}"):
                            update_salary_rate(s['id'], new_rate, str(eff_date))
                            st.success("Rate updated!")

                    st.write("**Add Advance / एडवांस**")
                    adv_col1, adv_col2 = st.columns(2)
                    with adv_col1:
                        adv_amt = st.number_input("Amount ₹", min_value=0.0, key=f"adv_{s['id']}")
                    with adv_col2:
                        adv_note = st.text_input("Note", key=f"advn_{s['id']}")
                    if st.button("Add Advance", key=f"addbtn_{s['id']}"):
                        if adv_amt > 0:
                            add_advance(s['id'], adv_amt, adv_note)
                            st.success(f"₹{adv_amt} advance added!")
        else:
            st.info("No staff added yet.")

    with tab2:
        with st.form("add_staff_form"):
            name = st.text_input("Name / नाम")
            col1, col2 = st.columns(2)
            with col1:
                join_date = st.date_input("Joining Date / जॉइनिंग तारीख", value=today)
            with col2:
                monthly_rate = st.number_input("Monthly Salary / मासिक वेतन (₹)", min_value=0.0, step=500.0)
            if st.form_submit_button("Add Staff / स्टाफ जोड़ें", use_container_width=True):
                if name and monthly_rate > 0:
                    add_staff(shop, name, str(join_date), monthly_rate)
                    st.success(f"✅ {name} added!")
                else:
                    st.error("Name and salary required.")

    with tab3:
        staff = get_staff(shop)
        if not staff:
            st.info("No staff added yet.")
            return

        col1, col2 = st.columns(2)
        with col1:
            sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                                      format_func=lambda m: datetime(2000, m, 1).strftime("%B"),
                                      key="sal_month")
        with col2:
            sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1, key="sal_year")

        st.divider()
        total_payable = 0
        for s in staff:
            sal = get_monthly_salary(s['id'], sel_month, sel_year)
            advances = get_advances(s['id'], sel_month, sel_year)
            total_payable += max(sal['net_payable'], 0)

            with st.expander(f"👤 {s['name']} — Net: ₹{sal['net_payable']:,.0f}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Days Present", f"{sal['days_present']}/{sal['days_in_month']}")
                c2.metric("Earned / कमाई", f"₹{sal['earned']:,.0f}")
                c3.metric("Advances / एडवांस", f"₹{sal['advances']:,.0f}")
                c4.metric("Net Payable / देय", f"₹{sal['net_payable']:,.0f}",
                           delta_color="inverse" if sal['net_payable'] < 0 else "normal")

                if advances:
                    st.write("**Advance Details:**")
                    for adv in advances:
                        st.write(f"• {adv['date']}: ₹{adv['amount']} — {adv['note'] or '-'}")

        st.metric("**Total Payable This Month**", f"₹{total_payable:,.0f}")


def show_attendance(shop, today):
    st.title("📅 Attendance / हाज़िरी")
    staff = get_staff(shop)

    if not staff:
        st.info("No staff added. Add staff first.")
        return

    col1, col2 = st.columns(2)
    with col1:
        att_date = st.date_input("Date / तारीख", value=today)

    st.divider()
    st.write(f"**Mark attendance for {att_date.strftime('%d %B %Y')}**")

    for s in staff:
        existing = get_attendance(s['id'], att_date.month, att_date.year)
        day_record = next((a for a in existing if a['date'] == str(att_date)), None)
        current = bool(day_record['present']) if day_record else False

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"👤 **{s['name']}**")
        with col2:
            present = st.checkbox("Present / उपस्थित", value=current, key=f"att_{s['id']}_{att_date}")
            if present != current:
                mark_attendance(s['id'], att_date, present)
                st.rerun()

    st.divider()
    st.subheader("Monthly Attendance / मासिक हाज़िरी")
    sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                              format_func=lambda m: datetime(2000, m, 1).strftime("%B"),
                              key="att_month_view")
    sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1, key="att_year_view")

    for s in staff:
        att = get_attendance(s['id'], sel_month, sel_year)
        days_present = sum(1 for a in att if a['present'])
        days_in_month = calendar.monthrange(sel_year, sel_month)[1]
        st.write(f"**{s['name']}**: {days_present}/{days_in_month} days present")
