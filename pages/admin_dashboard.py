import streamlit as st
from datetime import date, datetime
import calendar
from database import (
    get_all_stock, get_all_shops_monthly_sales, get_monthly_sales,
    get_monthly_expenses, get_pending_orders, fulfill_order,
    get_all_staff, get_monthly_salary, get_advances,
    LOCAL_ITEMS, MARKET_ITEMS, SHOPS
)
from pdf_generator import generate_restock_pdf

def show():
    st.sidebar.markdown("### 🌿 Admin Panel")
    st.sidebar.markdown("*All Shops View*")

    page = st.sidebar.radio("Menu / मेनू", [
        "📊 All Shops Overview",
        "📦 All Stock / सभी स्टॉक",
        "🔄 Pending Orders / ऑर्डर",
        "👷 Manage Staff & Salary",
        "📄 Generate PDF / PDF बनाएं",
        "📅 Monthly Report / मासिक रिपोर्ट",
        "📈 Graphs / ग्राफ",
    ])

    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.shop_name = None
        st.rerun()

    today = date.today()

    if page == "📊 All Shops Overview":
        show_overview(today)
    elif page == "📦 All Stock / सभी स्टॉक":
        show_all_stock()
    elif page == "🔄 Pending Orders / ऑर्डर":
        show_pending_orders()
    elif page == "👷 Manage Staff & Salary":
        show_manage_staff(today)
    elif page == "📈 Graphs / ग्राफ":
        show_graphs(today)
    elif page == "📄 Generate PDF / PDF बनाएं":
        show_pdf_generator()
    elif page == "📅 Monthly Report / मासिक रिपोर्ट":
        show_monthly_report(today)


def show_overview(today):
    st.title("📊 All Shops Overview / सभी दुकानें")

    col1, col2 = st.columns(2)
    with col1:
        sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                                  format_func=lambda m: datetime(2000, m, 1).strftime("%B"))
    with col2:
        sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1)

    pm = sel_month - 1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year - 1

    sales_this = get_all_shops_monthly_sales(sel_month, sel_year)
    sales_prev = get_all_shops_monthly_sales(pm, py)

    import pandas as pd
    rows = []
    for shop in SHOPS:
        this_month = sales_this.get(shop, 0) or 0
        prev_month = sales_prev.get(shop, 0) or 0
        expenses = get_monthly_expenses(shop, sel_month, sel_year)
        total_exp = sum(e['amount'] for e in expenses)
        profit = this_month - total_exp
        change = this_month - prev_month

        rows.append({
            "Shop": shop,
            "Sales ₹": this_month,
            "Expenses ₹": total_exp,
            "Profit/Loss ₹": profit,
            "vs Last Month ₹": change,
        })

    df = pd.DataFrame(rows)
    total_row = pd.DataFrame([{
        "Shop": "TOTAL",
        "Sales ₹": df["Sales ₹"].sum(),
        "Expenses ₹": df["Expenses ₹"].sum(),
        "Profit/Loss ₹": df["Profit/Loss ₹"].sum(),
        "vs Last Month ₹": df["vs Last Month ₹"].sum(),
    }])
    df = pd.concat([df, total_row], ignore_index=True)


    st.dataframe(df, use_container_width=True, height=600)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Sales", f"₹{df[df['Shop']!='TOTAL']['Sales ₹'].sum():,.0f}")
    m2.metric("Total Expenses", f"₹{df[df['Shop']!='TOTAL']['Expenses ₹'].sum():,.0f}")
    m3.metric("Total Profit", f"₹{df[df['Shop']!='TOTAL']['Profit/Loss ₹'].sum():,.0f}")


def show_all_stock():
    st.title("📦 All Shops Stock / सभी स्टॉक")

    stock = get_all_stock()
    if not stock:
        st.info("No stock data yet. Shops need to set their initial stock.")
        return

    import pandas as pd
    df = pd.DataFrame(stock)

    sel_shop = st.selectbox("Filter by Shop", ["All"] + SHOPS)
    if sel_shop != "All":
        df = df[df['shop_name'] == sel_shop]

    tab1, tab2 = st.tabs(["By Shop", "By Item"])

    with tab1:
        for shop in (SHOPS if sel_shop == "All" else [sel_shop]):
            shop_stock = df[df['shop_name'] == shop]
            if not shop_stock.empty:
                with st.expander(f"🏪 {shop} ({len(shop_stock)} items)"):
                    display = shop_stock[['item_name', 'item_type', 'quantity', 'updated_at']].copy()
                    display.columns = ['Item', 'Type', 'Qty', 'Updated']
                    display['Type'] = display['Type'].map({'local': '🟢 Local', 'market': '🔵 Market'})
                    st.dataframe(display, use_container_width=True)

    with tab2:
        pivot = df.pivot_table(index='item_name', columns='shop_name', values='quantity', fill_value=0)
        st.dataframe(pivot, use_container_width=True)


def show_pending_orders():
    st.title("🔄 Pending Restock Orders / बकाया ऑर्डर")

    orders = get_pending_orders()

    if not orders:
        st.success("✅ No pending orders!")
        return

    # Group by shop
    from itertools import groupby
    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    for shop, shop_orders in orders_by_shop.items():
        with st.expander(f"🏪 {shop} — {len(shop_orders)} items pending", expanded=True):
            for order in shop_orders:
                item = order['item_name']
                item_type = 'market' if item in MARKET_ITEMS else 'local'
                type_label = "🔵 Market" if item_type == 'market' else "🟢 Local"

                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(f"**{item}** {type_label}")
                    st.caption(f"Ordered: {order['order_date']}")
                with col2:
                    st.write(f"Qty: **{order['quantity']}**")
                with col3:
                    if MARKET_ITEMS.get(item, 0):
                        price = MARKET_ITEMS[item]
                        cost = price * order['quantity']
                        st.write(f"₹{cost:,.0f}")
                with col4:
                    if st.button("✅ Fulfill", key=f"ful_{order['id']}"):
                        fulfill_order(order['id'], shop, item, order['quantity'], item_type)
                        st.success(f"Fulfilled {item} for {shop}!")
                        st.rerun()


def show_all_salary(today):
    st.title("👷 All Staff Salary / सभी कर्मचारी वेतन")

    col1, col2 = st.columns(2)
    with col1:
        sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                                  format_func=lambda m: datetime(2000, m, 1).strftime("%B"))
    with col2:
        sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1)

    all_staff = get_all_staff()
    if not all_staff:
        st.info("No staff added yet.")
        return

    import pandas as pd
    rows = []
    for s in all_staff:
        sal = get_monthly_salary(s['id'], sel_month, sel_year)
        rows.append({
            "Shop": s['shop_name'],
            "Staff": s['name'],
            "Days Present": f"{sal['days_present']}/{sal['days_in_month']}",
            "Rate ₹": sal['rate'],
            "Earned ₹": sal['earned'],
            "Advances ₹": sal['advances'],
            "Net Payable ₹": sal['net_payable'],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.metric("Total Payable", f"₹{df['Net Payable ₹'].sum():,.0f}")


def show_pdf_generator():
    st.title("📄 Generate Restock PDF / PDF बनाएं")
    st.info("This generates a PDF from all pending orders — split into Local and Market sections (like your existing sheet).")

    orders = get_pending_orders()
    if not orders:
        st.warning("No pending orders to generate PDF from.")
        return

    # Show preview
    from itertools import groupby
    local_orders = [o for o in orders if o['item_name'] not in MARKET_ITEMS]
    market_orders = [o for o in orders if o['item_name'] in MARKET_ITEMS]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Local Items Preview")
        orders_by_shop = {}
        for o in local_orders:
            orders_by_shop.setdefault(o['shop_name'], []).append(o)
        for shop, items in orders_by_shop.items():
            st.write(f"**{shop}**")
            for item in items:
                st.write(f"  • {item['item_name']}: {item['quantity']}")

    with col2:
        st.subheader("🔵 Market Items Preview")
        orders_by_shop2 = {}
        for o in market_orders:
            orders_by_shop2.setdefault(o['shop_name'], []).append(o)
        total_cost = 0
        for shop, items in orders_by_shop2.items():
            st.write(f"**{shop}**")
            for item in items:
                price = MARKET_ITEMS.get(item['item_name'], 0)
                cost = price * item['quantity']
                total_cost += cost
                st.write(f"  • {item['item_name']}: {item['quantity']} (₹{cost:,.0f})")
        if total_cost:
            st.metric("Total Market Cost", f"₹{total_cost:,.0f}")

    st.divider()
    if st.button("📄 Generate & Download PDF", use_container_width=True, type="primary"):
        pdf_bytes = generate_restock_pdf(orders)
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"restock_order_{date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )


def show_monthly_report(today):
    st.title("📅 Monthly Report / मासिक रिपोर्ट")

    col1, col2, col3 = st.columns(3)
    with col1:
        sel_shop = st.selectbox("Shop", SHOPS)
    with col2:
        sel_month = st.selectbox("Month", range(1, 13), index=today.month - 1,
                                  format_func=lambda m: datetime(2000, m, 1).strftime("%B"))
    with col3:
        sel_year = st.selectbox("Year", [today.year - 1, today.year], index=1)

    st.divider()

    # Sales
    sales = get_monthly_sales(sel_shop, sel_month, sel_year)
    total_sales = sum(s['cash_amount'] + s['online_amount'] for s in sales)
    total_cash = sum(s['cash_amount'] for s in sales)
    total_online = sum(s['online_amount'] for s in sales)

    # Expenses
    expenses = get_monthly_expenses(sel_shop, sel_month, sel_year)
    total_exp = sum(e['amount'] for e in expenses)

    # Salary
    staff = [s for s in get_all_staff() if s['shop_name'] == sel_shop]
    total_salary = 0
    for s in staff:
        sal = get_monthly_salary(s['id'], sel_month, sel_year)
        total_salary += max(sal['net_payable'], 0)

    # Prev month for comparison
    pm = sel_month - 1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year - 1
    prev_sales_data = get_monthly_sales(sel_shop, pm, py)
    prev_total = sum(s['cash_amount'] + s['online_amount'] for s in prev_sales_data)

    profit = total_sales - total_exp - total_salary

    st.subheader(f"📊 {sel_shop} — {datetime(2000, sel_month, 1).strftime('%B')} {sel_year}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sales", f"₹{total_sales:,.0f}", delta=f"₹{total_sales - prev_total:,.0f} vs prev month")
    m2.metric("Expenses", f"₹{total_exp:,.0f}")
    m3.metric("Salary Cost", f"₹{total_salary:,.0f}")
    m4.metric("Net Profit/Loss", f"₹{profit:,.0f}",
               delta_color="inverse" if profit < 0 else "normal")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Sales Breakdown**")
        st.write(f"Cash: ₹{total_cash:,.0f}")
        st.write(f"Online: ₹{total_online:,.0f}")

        if sales:
            import pandas as pd
            df = pd.DataFrame(sales)[['date', 'cash_amount', 'online_amount']]
            df['total'] = df['cash_amount'] + df['online_amount']
            df.columns = ['Date', 'Cash', 'Online', 'Total']
            st.dataframe(df, use_container_width=True)

    with col2:
        st.write("**Expenses**")
        if expenses:
            import pandas as pd
            df_exp = pd.DataFrame(expenses)[['date', 'description', 'amount']]
            df_exp.columns = ['Date', 'Description', 'Amount ₹']
            st.dataframe(df_exp, use_container_width=True)
        else:
            st.info("No expenses this month.")

        st.write("**Staff Salary**")
        for s in staff:
            sal = get_monthly_salary(s['id'], sel_month, sel_year)
            st.write(f"• {s['name']}: ₹{sal['net_payable']:,.0f} ({sal['days_present']} days)")


def show_manage_staff(today):
    st.title("👷 Manage Staff & Salary / स्टाफ और वेतन")

    sel_shop = st.selectbox("Select Shop", SHOPS)
    tab1, tab2, tab3, tab4 = st.tabs(["Staff List", "Add Staff", "Salary Report", "Attendance"])

    from database import (get_staff, add_staff, get_monthly_salary, get_advances,
                           add_advance, update_salary_rate, mark_attendance,
                           get_attendance, get_sub_users, add_sub_user)
    import calendar

    with tab1:
        staff = get_staff(sel_shop)
        if not staff:
            st.info("No staff for this shop.")
        for s in staff:
            with st.expander(f"👤 {s['name']} — Rs {s['current_rate'] or 0:,.0f}/month  |  Joined: {s['join_date']}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_rate = st.number_input("New Rate / नई दर", min_value=0.0,
                                                value=float(s['current_rate'] or 0), key=f"ar_{s['id']}")
                    eff_date = st.date_input("Effective From", value=today, key=f"ae_{s['id']}")
                    if st.button("Update Rate", key=f"au_{s['id']}"):
                        update_salary_rate(s['id'], new_rate, str(eff_date))
                        st.success("Rate updated!")
                with col2:
                    adv_amt  = st.number_input("Advance Amount Rs", min_value=0.0, key=f"aa_{s['id']}")
                    adv_note = st.text_input("Note", key=f"an_{s['id']}")
                    if st.button("Add Advance", key=f"ab_{s['id']}"):
                        if adv_amt > 0:
                            add_advance(s['id'], adv_amt, adv_note)
                            st.success(f"Rs {adv_amt} advance added!")

        st.divider()
        st.subheader("Sub Users / सब यूज़र")
        sub_users = get_sub_users(sel_shop)
        for su in sub_users:
            st.write(f"👤 **{su['display_name']}** — login: `{su['username']}`")
        with st.form(f"sub_{sel_shop}"):
            c1, c2, c3 = st.columns(3)
            with c1: su_name = st.text_input("Name")
            with c2: su_user = st.text_input("Username")
            with c3: su_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Add Sub User"):
                if su_name and su_user and su_pass:
                    ok = add_sub_user(sel_shop, su_user, su_pass, su_name)
                    st.success(f"Added {su_name}!") if ok else st.error("Username taken.")

    with tab2:
        with st.form(f"addstaff_{sel_shop}"):
            name = st.text_input("Name / नाम")
            c1, c2 = st.columns(2)
            with c1: join_date = st.date_input("Joining Date", value=today)
            with c2: rate = st.number_input("Monthly Salary Rs", min_value=0.0, step=500.0)
            if st.form_submit_button("Add Staff", use_container_width=True):
                if name and rate > 0:
                    add_staff(sel_shop, name, str(join_date), rate)
                    st.success(f"{name} added!")

    with tab3:
        staff = get_staff(sel_shop)
        c1, c2 = st.columns(2)
        with c1:
            sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                      format_func=lambda m: datetime(2000,m,1).strftime("%B"), key="sm_adm")
        with c2:
            sel_year = st.selectbox("Year", [today.year-1, today.year], index=1, key="sy_adm")

        total_pay = 0
        for s in staff:
            sal = get_monthly_salary(s['id'], sel_month, sel_year)
            total_pay += max(sal['net_payable'], 0)
            advances = get_advances(s['id'], sel_month, sel_year)
            with st.expander(f"👤 {s['name']} — Net: Rs {sal['net_payable']:,.0f}"):
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Days Present", f"{sal['days_present']}/{sal['days_in_month']}")
                c2.metric("Earned", f"Rs {sal['earned']:,.0f}")
                c3.metric("Advances", f"Rs {sal['advances']:,.0f}")
                c4.metric("Net Payable", f"Rs {sal['net_payable']:,.0f}")
                for adv in advances:
                    st.caption(f"• {adv['date']}: Rs {adv['amount']} — {adv['note'] or '-'}")
        if staff:
            st.metric("Total Payable", f"Rs {total_pay:,.0f}")

    with tab4:
        staff = get_staff(sel_shop)
        att_date = st.date_input("Date", value=today, key="att_admin")
        for s in staff:
            existing = get_attendance(s['id'], att_date.month, att_date.year)
            day_rec = next((a for a in existing if a['date'] == str(att_date)), None)
            current = bool(day_rec['present']) if day_rec else False
            col1, col2 = st.columns([3,1])
            with col1: st.write(f"👤 **{s['name']}**")
            with col2:
                present = st.checkbox("Present", value=current, key=f"adm_att_{s['id']}_{att_date}")
                if present != current:
                    mark_attendance(s['id'], att_date, present)
                    st.rerun()


def show_graphs(today):
    st.title("📈 Graphs / ग्राफ")
    import pandas as pd

    col1, col2 = st.columns(2)
    with col1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"), key="gm")
    with col2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1, key="gy")

    pm = sel_month-1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year-1

    sales_this = get_all_shops_monthly_sales(sel_month, sel_year)
    sales_prev = get_all_shops_monthly_sales(pm, py)

    rows = []
    for shop in SHOPS:
        this = sales_this.get(shop, 0) or 0
        prev = sales_prev.get(shop, 0) or 0
        rows.append({"Shop": shop, "This Month": this, "Last Month": prev})

    df = pd.DataFrame(rows)
    df = df[(df['This Month'] > 0) | (df['Last Month'] > 0)]

    if df.empty:
        st.info("No sales data yet to show graphs.")
        return

    st.subheader("Sales This Month vs Last Month")
    st.bar_chart(df.set_index('Shop')[['This Month','Last Month']])

    st.divider()
    st.subheader("Top Shops This Month")
    top = df.sort_values('This Month', ascending=False).head(10)
    st.bar_chart(top.set_index('Shop')['This Month'])

    st.divider()
    st.subheader("Growth vs Last Month")
    df['Growth'] = df['This Month'] - df['Last Month']
    df_sorted = df.sort_values('Growth', ascending=False)
    st.bar_chart(df_sorted.set_index('Shop')['Growth'])
