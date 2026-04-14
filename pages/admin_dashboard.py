import streamlit as st
from datetime import date, datetime
import calendar
from database import (
    add_custom_item, get_all_items_managed, toggle_item_active,
    get_admin_users, add_admin_user, deactivate_user,
    add_supply, get_monthly_supply, get_all_shops_monthly_supply,
    get_profit_settings, update_profit_setting, delete_supply,
    get_all_shops_stock_status, get_approx_stock,
    SUPPLY_CATEGORIES, PAAN_ITEMS, GODOWN_ITEMS,
    get_all_stock, get_all_shops_monthly_sales, get_monthly_sales,
    get_monthly_expenses, get_pending_orders_filtered, fulfill_orders_bulk,
    get_all_staff, get_monthly_salary, get_advances,
    get_staff, add_staff, update_salary_rate, add_advance,
    mark_attendance, get_attendance,
    get_sub_users, add_sub_user, link_subuser_to_staff,
    get_all_users, update_user_password,
    LOCAL_ITEMS, MARKET_ITEMS, SHOPS
)
from pdf_generator import generate_restock_pdf

def show():
    if not st.session_state.get("user") or st.session_state.get("role") != "admin":
        st.error("🔒 Access denied.")
        st.stop()

    st.sidebar.markdown("### 🌿 Admin Panel")
    page = st.sidebar.radio("Menu", [
        "📊 All Shops Overview",
        "📦 All Stock",
        "🔄 Restock Orders",
        "👷 Staff & Salary",
        "👥 User Management",
        "📄 Generate PDF",
        "📅 Monthly Report",
        "📈 Graphs",
        "💼 My Supply & Costs",
        "🏪 Shop Progress",
        "📦 Manage Items",
        "👑 Admin Users",
    ])
    if st.sidebar.button("🚪 Logout"):
        for k in ["user","role","shop_name"]: st.session_state[k] = None
        st.rerun()

    today = date.today()
    if page == "📊 All Shops Overview":     show_overview(today)
    elif page == "📦 All Stock":            show_all_stock()
    elif page == "🔄 Restock Orders":       show_orders(today)
    elif page == "👷 Staff & Salary":       show_staff(today)
    elif page == "👥 User Management":      show_users()
    elif page == "📄 Generate PDF":         show_pdf(today)
    elif page == "📅 Monthly Report":       show_monthly_report(today)
    elif page == "📈 Graphs":               show_graphs(today)
    elif page == "💼 My Supply & Costs":    show_supply(today)
    elif page == "🏪 Shop Progress":           show_shop_progress()
    elif page == "📦 Manage Items":              show_manage_items()
    elif page == "👑 Admin Users":               show_admin_users()


# ── Overview ───────────────────────────────────────────
def show_overview(today):
    st.title("📊 All Shops Overview")
    import pandas as pd
    c1, c2 = st.columns(2)
    with c1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    pm = sel_month-1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year-1

    sales_this = get_all_shops_monthly_sales(sel_month, sel_year)
    sales_prev = get_all_shops_monthly_sales(pm, py)

    rows = []
    for shop in SHOPS:
        this = sales_this.get(shop,0) or 0
        prev = sales_prev.get(shop,0) or 0
        exps = get_monthly_expenses(shop, sel_month, sel_year)
        exp  = sum(e['amount'] for e in exps)
        rows.append({"Shop":shop, "Sales":this, "Expenses":exp,
                     "Profit":this-exp, "vs Last Month":this-prev})

    df = pd.DataFrame(rows)
    total = {"Shop":"TOTAL","Sales":df.Sales.sum(),"Expenses":df.Expenses.sum(),
             "Profit":df.Profit.sum(),"vs Last Month":df["vs Last Month"].sum()}
    df = pd.concat([df, pd.DataFrame([total])], ignore_index=True)
    st.dataframe(df, use_container_width=True, height=600)

    nt = df[df.Shop != 'TOTAL']
    c1,c2,c3 = st.columns(3)
    c1.metric("Total Sales",    f"Rs {nt.Sales.sum():,.0f}")
    c2.metric("Total Expenses", f"Rs {nt.Expenses.sum():,.0f}")
    c3.metric("Total Profit",   f"Rs {nt.Profit.sum():,.0f}")


# ── Stock ──────────────────────────────────────────────
def show_all_stock():
    st.title("📦 All Stock")
    stock = get_all_stock()
    if not stock:
        st.info("No stock data yet.")
        return
    import pandas as pd
    df = pd.DataFrame(stock)
    sel = st.selectbox("Filter by Shop", ["All"] + SHOPS)
    if sel != "All":
        df = df[df.shop_name == sel]

    tab1, tab2 = st.tabs(["By Shop", "By Item"])
    with tab1:
        for shop in (SHOPS if sel=="All" else [sel]):
            sd = df[df.shop_name==shop]
            if not sd.empty:
                with st.expander(f"🏪 {shop} ({len(sd)} items)"):
                    d = sd[['item_name','item_type','quantity','updated_at']].copy()
                    d.columns = ['Item','Type','Qty','Updated']
                    d['Type'] = d['Type'].map({'local':'🟢 Local','market':'🔵 Market'})
                    st.dataframe(d, use_container_width=True)
    with tab2:
        if not df.empty:
            pivot = df.pivot_table(index='item_name', columns='shop_name', values='quantity', fill_value=0)
            st.dataframe(pivot, use_container_width=True)


# ── Restock Orders ─────────────────────────────────────
def show_orders(today):
    st.title("🔄 Restock Orders")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        date_from = st.date_input("From", value=today)
    with col2:
        date_to = st.date_input("To", value=today)
    with col3:
        win_filter = st.selectbox("Window", ["All", "Day only", "Night only"])
    with col4:
        merge = st.checkbox("Merge duplicates", value=True)

    wtype = None
    if win_filter == "Day only":   wtype = "day"
    if win_filter == "Night only": wtype = "night"

    orders = get_pending_orders_filtered(date_from, date_to, wtype, merge)

    if not orders:
        st.success("✅ No pending orders matching filters!")
        return

    st.caption(f"Showing {len(orders)} order lines")

    orders_by_shop = {}
    for o in orders:
        orders_by_shop.setdefault(o['shop_name'], []).append(o)

    for shop, shop_orders in orders_by_shop.items():
        # Separate extra notes from real items
        extra_notes = [o for o in shop_orders if o['item_name'] == '__EXTRA__']
        real_orders  = [o for o in shop_orders if o['item_name'] != '__EXTRA__']

        label_count = f"{len(real_orders)} items" + (" + 📝 note" if extra_notes else "")
        with st.expander(f"🏪 {shop} — {label_count}", expanded=True):
            # Show extra notes first
            for en in extra_notes:
                st.info(f"📝 Extra note: **{en.get('extra_note','')}**")

            for order in real_orders:
                item  = order['item_name']
                itype = 'market' if item in MARKET_ITEMS else 'local'
                price = MARKET_ITEMS.get(item, 0)
                ids   = order.get('_ids', [order['id']])

                # Group label
                from database import GODOWN_ITEMS, PAAN_ITEMS, MORNING_ITEMS_DISPLAY
                if item in GODOWN_ITEMS:      grp = "🟢 Godown"
                elif item in PAAN_ITEMS:      grp = "🌿 Paan"
                elif item in MORNING_ITEMS_DISPLAY: grp = "⬛ Morning"
                else:                         grp = "🔵 Market"

                c1,c2,c3,c4,c5 = st.columns([3,1,1,1,1])
                with c1:
                    st.write(f"**{item}** {grp}")
                    if order.get('window_type') == 'night':
                        st.caption("🌙 Night order")
                with c2:
                    st.write(f"Qty: **{order['quantity']}**")
                with c3:
                    if price:
                        st.write(f"Rs {price*order['quantity']:,.0f}")
                with c4:
                    st.caption(f"{order.get('order_date','')}")
                with c5:
                    if st.button("✅ Fulfill", key=f"ful_{shop}_{item}"):
                        fulfill_orders_bulk(ids, shop, item, order['quantity'], itype)
                        st.success(f"Fulfilled {item}!")
                        st.rerun()


# ── Staff & Salary ─────────────────────────────────────
def show_staff(today):
    st.title("👷 Staff & Salary")
    sel_shop = st.selectbox("Shop", SHOPS)

    tab1, tab2, tab3, tab4 = st.tabs(["Staff List", "Add Staff", "Salary Report", "Attendance"])

    with tab1:
        staff = get_staff(sel_shop)
        if not staff:
            st.info("No staff for this shop.")
        for s in staff:
            with st.expander(f"👤 {s['name']} — Rs {s['current_rate'] or 0:,.0f}/month | Joined: {s['join_date']}"):
                c1,c2 = st.columns(2)
                with c1:
                    new_rate = st.number_input("New Rate Rs", min_value=0.0,
                                                value=float(s['current_rate'] or 0), key=f"nr_{s['id']}")
                    eff = st.date_input("Effective From", value=today, key=f"ef_{s['id']}")
                    if st.button("Update Rate", key=f"ur_{s['id']}"):
                        update_salary_rate(s['id'], new_rate, str(eff))
                        st.success("Updated!")
                with c2:
                    adv = st.number_input("Advance Rs", min_value=0.0, key=f"adv_{s['id']}")
                    anote = st.text_input("Note", key=f"an_{s['id']}")
                    if st.button("Add Advance", key=f"ab_{s['id']}"):
                        if adv > 0:
                            add_advance(s['id'], adv, anote)
                            st.success(f"Rs {adv} added!")

        st.divider()
        st.subheader("Sub Users / Workers")
        sub_users = get_sub_users(sel_shop)
        staff_list = get_staff(sel_shop)

        for su in sub_users:
            linked = next((s for s in staff_list if s['id'] == su.get('staff_id')), None)
            with st.expander(f"👤 {su['display_name']} | login: {su['username']}"):
                linked_name = linked['name'] if linked else "Not linked"
                st.write(f"Linked to salary record: **{linked_name}**")
                if staff_list:
                    opts = ["-- None --"] + [s['name'] for s in staff_list]
                    curr_idx = next((i+1 for i,s in enumerate(staff_list) if s['id']==su.get('staff_id')), 0)
                    sel_staff = st.selectbox("Link to staff record", opts, index=curr_idx, key=f"lnk_{su['id']}")
                    if st.button("Save Link", key=f"slnk_{su['id']}"):
                        if sel_staff != "-- None --":
                            sid = next(s['id'] for s in staff_list if s['name']==sel_staff)
                            link_subuser_to_staff(su['username'], sid)
                            st.success("Linked!")

        st.divider()
        with st.form(f"addsub_{sel_shop}"):
            st.write("**Add Sub User / Worker**")
            c1,c2,c3 = st.columns(3)
            with c1: sname = st.text_input("Name")
            with c2: suser = st.text_input("Username")
            with c3: spass = st.text_input("Password", type="password")
            if st.form_submit_button("Add"):
                if sname and suser and spass:
                    ok = add_sub_user(sel_shop, suser, spass, sname)
                    st.success(f"Added {sname}!") if ok else st.error("Username taken.")

    with tab2:
        with st.form(f"addstaff_{sel_shop}"):
            name = st.text_input("Staff Name")
            c1,c2 = st.columns(2)
            with c1: jdate = st.date_input("Joining Date", value=today)
            with c2: rate  = st.number_input("Monthly Salary Rs", min_value=0.0, step=500.0)
            if st.form_submit_button("Add Staff", use_container_width=True):
                if name and rate > 0:
                    add_staff(sel_shop, name, str(jdate), rate)
                    st.success(f"{name} added!")

    with tab3:
        staff = get_staff(sel_shop)
        c1,c2 = st.columns(2)
        with c1:
            sm = st.selectbox("Month", range(1,13), index=today.month-1,
                               format_func=lambda m: datetime(2000,m,1).strftime("%B"), key="sal_m")
        with c2:
            sy = st.selectbox("Year", [today.year-1, today.year], index=1, key="sal_y")

        total_pay = 0
        for s in staff:
            sal = get_monthly_salary(s['id'], sm, sy)
            total_pay += max(sal['net_payable'], 0)
            advances = get_advances(s['id'], sm, sy)
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
        att_date = st.date_input("Date", value=today, key="att_d")
        for s in staff:
            existing = get_attendance(s['id'], att_date.month, att_date.year)
            rec = next((a for a in existing if a['date']==str(att_date)), None)
            curr = bool(rec['present']) if rec else False
            c1,c2 = st.columns([3,1])
            with c1: st.write(f"👤 **{s['name']}**")
            with c2:
                p = st.checkbox("Present", value=curr, key=f"att_{s['id']}_{att_date}")
                if p != curr:
                    mark_attendance(s['id'], att_date, p)
                    st.rerun()


# ── User Management ────────────────────────────────────
def show_users():
    st.title("👥 User Management")
    users = get_all_users()

    st.subheader("Shop Users")
    for u in users:
        with st.expander(f"🏪 {u['shop_name']} — login: `{u['username']}`"):
            c1, c2 = st.columns(2)
            with c1:
                new_pass = st.text_input("New Password", type="password", key=f"up_{u['username']}")
            with c2:
                st.write("")
                st.write("")
                if st.button("Update Password", key=f"upb_{u['username']}"):
                    if new_pass:
                        update_user_password(u['username'], new_pass)
                        st.success("Password updated!")
                    else:
                        st.error("Enter a password.")

    st.divider()
    st.subheader("Admin Password")
    with st.form("admin_pass"):
        new_admin = st.text_input("New Admin Password", type="password")
        if st.form_submit_button("Update"):
            if new_admin:
                update_user_password("admin", new_admin)
                st.success("Admin password updated!")


# ── PDF Generator ──────────────────────────────────────
def show_pdf(today):
    st.title("📄 Generate Restock PDF")

    col1, col2, col3 = st.columns(3)
    with col1:
        date_from = st.date_input("From", value=today)
    with col2:
        date_to = st.date_input("To", value=today)
    with col3:
        win_filter = st.selectbox("Include", ["Day orders only", "All orders", "Night orders only"])

    wtype = "day" if win_filter == "Day orders only" else ("night" if win_filter == "Night orders only" else None)
    orders = get_pending_orders_filtered(date_from, date_to, wtype, merge_duplicates=True)

    if not orders:
        st.warning("No orders for selected filters.")
        return

    local_orders  = [o for o in orders if o['item_name'] not in MARKET_ITEMS]
    market_orders = [o for o in orders if o['item_name'] in MARKET_ITEMS]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Local Items")
        obs = {}
        for o in local_orders:
            obs.setdefault(o['shop_name'],[]).append(o)
        for shop, items in obs.items():
            st.write(f"**{shop}**")
            for item in items:
                st.write(f"  • {item['item_name']}: {item['quantity']}")
    with col2:
        st.subheader("🔵 Market Items")
        obs2 = {}
        for o in market_orders:
            obs2.setdefault(o['shop_name'],[]).append(o)
        total_cost = 0
        for shop, items in obs2.items():
            st.write(f"**{shop}**")
            for item in items:
                price = MARKET_ITEMS.get(item['item_name'],0)
                cost = price * item['quantity']
                total_cost += cost
                st.write(f"  • {item['item_name']}: {item['quantity']} — Rs {cost:,.0f}")
        if total_cost:
            st.metric("Total Market Cost", f"Rs {total_cost:,.0f}")

    st.divider()
    if st.button("📄 Generate PDF", use_container_width=True, type="primary"):
        pdf_bytes = generate_restock_pdf(orders, show_costs=True)
        st.download_button("⬇️ Download PDF", data=pdf_bytes,
                           file_name=f"restock_{date_from}_to_{date_to}.pdf",
                           mime="application/pdf", use_container_width=True)


# ── Monthly Report ─────────────────────────────────────
def show_monthly_report(today):
    st.title("📅 Monthly Report")
    c1,c2,c3 = st.columns(3)
    with c1: sel_shop = st.selectbox("Shop", SHOPS)
    with c2:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c3:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    sales = get_monthly_sales(sel_shop, sel_month, sel_year)
    total_sales = sum(s['cash_amount']+s['online_amount'] for s in sales)
    total_cash  = sum(s['cash_amount'] for s in sales)
    total_online= sum(s['online_amount'] for s in sales)

    expenses    = get_monthly_expenses(sel_shop, sel_month, sel_year)
    total_exp   = sum(e['amount'] for e in expenses)

    staff = [s for s in get_all_staff() if s['shop_name']==sel_shop]
    total_salary = sum(max(get_monthly_salary(s['id'], sel_month, sel_year)['net_payable'],0) for s in staff)

    pm = sel_month-1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year-1
    prev = get_monthly_sales(sel_shop, pm, py)
    prev_total = sum(s['cash_amount']+s['online_amount'] for s in prev)

    profit = total_sales - total_exp - total_salary

    st.subheader(f"{sel_shop} — {datetime(2000,sel_month,1).strftime('%B')} {sel_year}")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Sales", f"Rs {total_sales:,.0f}", delta=f"Rs {total_sales-prev_total:,.0f}")
    c2.metric("Expenses", f"Rs {total_exp:,.0f}")
    c3.metric("Salary", f"Rs {total_salary:,.0f}")
    c4.metric("Net Profit", f"Rs {profit:,.0f}")

    st.divider()
    if sales:
        import pandas as pd
        df = pd.DataFrame(sales)[['date','cash_amount','online_amount']]
        df['total'] = df['cash_amount'] + df['online_amount']
        df.columns = ['Date','Cash','Online','Total']
        st.dataframe(df, use_container_width=True)

    if expenses:
        import pandas as pd
        df2 = pd.DataFrame(expenses)[['date','description','amount']]
        df2.columns = ['Date','Description','Amount']
        st.dataframe(df2, use_container_width=True)

    for s in staff:
        sal = get_monthly_salary(s['id'], sel_month, sel_year)
        st.write(f"• {s['name']}: Rs {sal['net_payable']:,.0f} ({sal['days_present']} days)")


# ── Graphs ─────────────────────────────────────────────
def show_graphs(today):
    st.title("📈 Graphs")
    import pandas as pd
    c1,c2 = st.columns(2)
    with c1:
        sel_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                  format_func=lambda m: datetime(2000,m,1).strftime("%B"))
    with c2:
        sel_year = st.selectbox("Year", [today.year-1, today.year], index=1)

    pm = sel_month-1 if sel_month > 1 else 12
    py = sel_year if sel_month > 1 else sel_year-1

    sales_this = get_all_shops_monthly_sales(sel_month, sel_year)
    sales_prev = get_all_shops_monthly_sales(pm, py)

    rows = [{"Shop":s, "This Month":sales_this.get(s,0) or 0,
             "Last Month":sales_prev.get(s,0) or 0} for s in SHOPS]
    df = pd.DataFrame(rows)
    df = df[(df['This Month']>0)|(df['Last Month']>0)]

    if df.empty:
        st.info("No sales data yet.")
        return

    st.subheader("This Month vs Last Month")
    st.bar_chart(df.set_index('Shop')[['This Month','Last Month']])

    st.divider()
    st.subheader("Top Shops This Month")
    st.bar_chart(df.sort_values('This Month', ascending=False).head(10).set_index('Shop')['This Month'])

    st.divider()
    df['Growth'] = df['This Month'] - df['Last Month']
    st.subheader("Growth vs Last Month")
    st.bar_chart(df.sort_values('Growth', ascending=False).set_index('Shop')['Growth'])


# ── My Supply & Costs ──────────────────────────────────
def show_supply(today):
    st.title("💼 My Supply & Costs")

    tab1, tab2, tab3 = st.tabs([
        "➕ Add Supply",
        "📊 Shop-wise Report",
        "⚙️ Profit % Settings"
    ])

    with tab1:
        st.subheader("Bulk Supply Entry — all shops at once")
        settings = get_profit_settings()
        pct_map = {s['category']: s['profit_percent'] for s in settings}

        c1, c2 = st.columns(2)
        with c1:
            sup_date = st.date_input("Date", value=today, key="bulk_date")
        with c2:
            category = st.selectbox("Category", [c for c, _ in SUPPLY_CATEGORIES], key="bulk_cat")

        profit_pct = pct_map.get(category, 20.0)
        st.caption(f"Profit % for **{category}**: {profit_pct}% → Expected = Cost × {1 + profit_pct/100:.2f}")

        with st.form("bulk_supply_form"):
            st.write(f"**Enter cost supplied to each shop (leave 0 to skip):**")
            shop_costs = {}
            cols = st.columns(4)
            for i, shop in enumerate(SHOPS):
                with cols[i%4]:
                    shop_costs[shop] = st.number_input(shop, min_value=0.0, step=10.0, key=f"bs_{shop}")

            note = st.text_input("Note (optional)", key="bulk_note")

            if st.form_submit_button("💾 Save All / सेव करें", use_container_width=True):
                saved = 0
                total_cost = 0
                for shop, cost in shop_costs.items():
                    if cost > 0:
                        add_supply(shop, sup_date, category, cost, profit_pct, note)
                        saved += 1
                        total_cost += cost
                if saved:
                    total_exp = total_cost * (1 + profit_pct/100)
                    st.success(f"✅ Saved for {saved} shops! Total cost: Rs {total_cost:,.0f} → Expected: Rs {total_exp:,.0f}")
                else:
                    st.warning("Enter cost for at least one shop.")

        st.divider()
        st.subheader("Recent Supply Log")
        c1, c2, c3 = st.columns(3)
        with c1:
            view_shop = st.selectbox("Shop", ["All"] + SHOPS, key="vs")
        with c2:
            view_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                       format_func=lambda m: datetime(2000,m,1).strftime("%B"), key="vm")
        with c3:
            view_year = st.selectbox("Year", [today.year-1, today.year], index=1, key="vy")

        shops_to_show = SHOPS if view_shop == "All" else [view_shop]
        import pandas as pd
        all_rows = []
        for shop in shops_to_show:
            rows = get_monthly_supply(shop, view_month, view_year)
            for r in rows:
                r['shop'] = shop
                all_rows.append(r)

        if all_rows:
            df = pd.DataFrame(all_rows)[['shop','supply_date','category','cost_amount','profit_percent','expected_revenue','note']]
            df.columns = ['Shop','Date','Category','Cost Rs','Profit %','Expected Rs','Note']
            st.dataframe(df, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cost",     f"Rs {df['Cost Rs'].sum():,.0f}")
            c2.metric("Total Expected", f"Rs {df['Expected Rs'].sum():,.0f}")
            c3.metric("Expected Profit",f"Rs {df['Expected Rs'].sum() - df['Cost Rs'].sum():,.0f}")
        else:
            st.info("No supply records for this period.")

    with tab2:
        st.subheader("Shop-wise Supply vs Actual Sales")
        c1, c2 = st.columns(2)
        with c1:
            rep_month = st.selectbox("Month", range(1,13), index=today.month-1,
                                      format_func=lambda m: datetime(2000,m,1).strftime("%B"), key="rm")
        with c2:
            rep_year = st.selectbox("Year", [today.year-1, today.year], index=1, key="ry")

        supply_data = get_all_shops_monthly_supply(rep_month, rep_year)
        sales_data  = get_all_shops_monthly_sales(rep_month, rep_year)

        import pandas as pd
        rows = []
        for shop in SHOPS:
            sup  = supply_data.get(shop, {})
            cost = sup.get('total_cost', 0) or 0
            exp  = sup.get('total_expected', 0) or 0
            actual = sales_data.get(shop, 0) or 0
            if cost > 0 or actual > 0:
                rows.append({
                    "Shop": shop,
                    "My Cost Rs": cost,
                    "Expected Revenue Rs": exp,
                    "Actual Sales Rs": actual,
                    "Gap Rs": actual - exp,
                })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Cost",     f"Rs {df['My Cost Rs'].sum():,.0f}")
            c2.metric("Expected",       f"Rs {df['Expected Revenue Rs'].sum():,.0f}")
            c3.metric("Actual Sales",   f"Rs {df['Actual Sales Rs'].sum():,.0f}")
            gap = df['Actual Sales Rs'].sum() - df['Expected Revenue Rs'].sum()
            c4.metric("Gap", f"Rs {gap:,.0f}",
                      help="Positive = shops earned more than expected. Negative = shortfall.")

            st.divider()
            st.subheader("Category Breakdown")
            # Show per-category totals for selected month
            all_supply = []
            for shop in SHOPS:
                rows2 = get_monthly_supply(shop, rep_month, rep_year)
                all_supply.extend(rows2)
            if all_supply:
                df2 = pd.DataFrame(all_supply)
                cat_summary = df2.groupby('category').agg(
                    Cost=('cost_amount','sum'),
                    Expected=('expected_revenue','sum')
                ).reset_index()
                cat_summary['Profit'] = cat_summary['Expected'] - cat_summary['Cost']
                st.dataframe(cat_summary, use_container_width=True)
        else:
            st.info("No supply data for this period.")

    with tab3:
        st.subheader("Profit % per Category")
        st.info("Set your expected profit margin for each category. This auto-fills when you add supply.")
        settings = get_profit_settings()

        with st.form("profit_settings"):
            new_vals = {}
            for s in settings:
                new_vals[s['category']] = st.number_input(
                    s['category'], min_value=0.0, max_value=200.0,
                    value=float(s['profit_percent']), step=1.0,
                    key=f"ps_{s['category']}"
                )
            if st.form_submit_button("Save Settings", use_container_width=True):
                for cat, pct in new_vals.items():
                    update_profit_setting(cat, pct)
                st.success("✅ Profit settings saved!")
                st.rerun()


# ── Shop Progress Dashboard ────────────────────────────
def show_shop_progress():
    st.title("🏪 Shop Progress / दुकान की स्थिति")

    from datetime import datetime as dt
    today = date.today()
    m, y = today.month, today.year
    pm = m-1 if m > 1 else 12
    py = y if m > 1 else y-1

    sales_this = get_all_shops_monthly_sales(m, y)
    sales_prev = get_all_shops_monthly_sales(pm, py)
    supply_data = get_all_shops_monthly_supply(m, y)
    stock_status = get_all_shops_stock_status()

    st.subheader(f"All Shops — {dt(2000,m,1).strftime('%B')} {y}")

    # CSS for colored tiles
    st.markdown("""
    <style>
    .shop-tile { padding:12px; border-radius:10px; margin:4px; text-align:center; }
    .tile-green  { background:#1b5e20; color:white; }
    .tile-yellow { background:#f57f17; color:white; }
    .tile-red    { background:#b71c1c; color:white; }
    .tile-gray   { background:#424242; color:white; }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    for i, shop in enumerate(SHOPS):
        this  = sales_this.get(shop, 0) or 0
        prev  = sales_prev.get(shop, 0) or 0
        sup   = supply_data.get(shop, {})
        exp   = sup.get('total_expected', 0) or 0
        stock = stock_status.get(shop, 'no_data')

        # Performance color
        if exp == 0:
            color = "gray"
            perf = "No data"
        elif this >= exp:
            color = "green"
            perf = f"✅ Rs {this:,.0f}"
        elif this >= exp * 0.8:
            color = "yellow"
            perf = f"⚠️ Rs {this:,.0f}"
        else:
            color = "red"
            perf = f"❌ Rs {this:,.0f}"

        stock_icon = {"good":"🟢","low":"🟡","out":"🔴","no_data":"⚪"}.get(stock,"⚪")

        with cols[i%4]:
            st.markdown(f"""
            <div class="shop-tile tile-{color}">
                <b>{shop}</b><br>
                {perf}<br>
                <small>Exp: Rs {exp:,.0f}</small><br>
                {stock_icon} Stock
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Detail View")
    sel = st.selectbox("Select Shop", SHOPS)
    approx = get_approx_stock(sel)
    if approx:
        import pandas as pd
        df = pd.DataFrame(approx)[['item','stocked','used','remaining','status']]
        df['status'] = df['status'].map({'good':'🟢 Good','medium':'🟡 Medium','low':'🟡 Low','out':'🔴 Out','unknown':'⚪ Unknown'})
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No stock data for this shop.")


# ── Manage Items ───────────────────────────────────────
def show_manage_items():
    st.title("📦 Manage Items")
    st.caption("Add new items or disable old ones. Changes apply to all shops.")

    CATEGORIES = [
        ('godown',  '🟢 Godown Items'),
        ('paan',    '🟤 Paan Items'),
        ('market',  '🔵 Market Items'),
        ('morning', '⬛ Morning Items (Tin/Cover/Katha)'),
    ]

    tab1, tab2 = st.tabs(["➕ Add Item", "📋 View / Disable"])

    with tab1:
        with st.form("add_item_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                item_name = st.text_input("Item Name / आइटम का नाम")
            with c2:
                category  = st.selectbox("Category", [c[0] for c in CATEGORIES],
                                          format_func=lambda x: next(c[1] for c in CATEGORIES if c[0]==x))
            with c3:
                price = st.number_input("Price Rs (0 if unknown)", min_value=0.0, step=10.0)

            if st.form_submit_button("Add Item", use_container_width=True):
                if item_name.strip():
                    ok = add_custom_item(item_name, category, price)
                    if ok:
                        st.success(f"✅ '{item_name}' added to {category}!")
                    else:
                        st.error("Item already exists.")
                else:
                    st.warning("Enter item name.")

    with tab2:
        items = get_all_items_managed()
        if not items:
            st.info("No custom items added yet. Built-in items cannot be disabled here — add items above.")
            return

        for cat_key, cat_label in CATEGORIES:
            cat_items = [i for i in items if i['category'] == cat_key]
            if not cat_items:
                continue
            st.subheader(cat_label)
            for item in cat_items:
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.write(f"**{item['item_name']}**")
                with c2:
                    if item['price'] > 0:
                        st.caption(f"Rs {item['price']:,.0f}")
                with c3:
                    active = bool(item['is_active'])
                    new_state = st.checkbox("Active", value=active, key=f"itm_{item['id']}")
                    if new_state != active:
                        toggle_item_active(item['item_name'], new_state)
                        st.rerun()


# ── Admin Users ────────────────────────────────────────
def show_admin_users():
    st.title("👑 Admin Users")
    st.caption("Add your brothers, dad — anyone who needs full admin access.")

    admins = get_admin_users()

    st.subheader("Current Admins")
    for a in admins:
        disabled = a['password'] == '__DISABLED__'
        with st.expander(f"{'❌' if disabled else '✅'} {a['username']} {'(disabled)' if disabled else ''}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_pass = st.text_input("New Password", type="password", key=f"ap_{a['username']}")
            with c2:
                st.write("")
                st.write("")
                if st.button("Update Password", key=f"apb_{a['username']}"):
                    if new_pass:
                        from database import update_user_password
                        update_user_password(a['username'], new_pass)
                        st.success("Updated!")
            with c3:
                st.write("")
                st.write("")
                if a['username'] != 'admin' and not disabled:
                    if st.button("Disable", key=f"apd_{a['username']}"):
                        deactivate_user(a['username'])
                        st.warning(f"{a['username']} disabled.")
                        st.rerun()

    st.divider()
    st.subheader("Add New Admin")
    with st.form("new_admin_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            uname = st.text_input("Username (for login)")
        with c2:
            upass = st.text_input("Password", type="password")
        with c3:
            dname = st.text_input("Name (e.g. Bhai, Papa)")
        if st.form_submit_button("Add Admin", use_container_width=True):
            if uname and upass:
                ok = add_admin_user(uname, upass, dname)
                if ok:
                    st.success(f"✅ {uname} added as admin! They can login now.")
                else:
                    st.error("Username already taken.")
            else:
                st.warning("Username and password required.")
