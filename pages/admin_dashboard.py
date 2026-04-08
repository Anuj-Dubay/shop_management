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
        "👷 All Staff & Salary",
        "📄 Generate PDF / PDF बनाएं",
        "📅 Monthly Report / मासिक रिपोर्ट",
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
    elif page == "👷 All Staff & Salary":
        show_all_salary(today)
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

    def color_profit(val):
        if isinstance(val, (int, float)):
            return 'color: green' if val >= 0 else 'color: red'
        return ''

    styled = df.style.applymap(color_profit, subset=["Profit/Loss ₹", "vs Last Month ₹"])
    st.dataframe(styled, use_container_width=True, height=600)

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
