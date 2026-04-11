# 🌿 Paan Shop Manager

Multi-shop management system — sales, stock, staff salary, restock PDF generation.

---

## 📁 File Structure

```
paan_app/
├── app.py                  ← Main entry point
├── database.py             ← All data logic (SQLite)
├── pdf_generator.py        ← Restock PDF (Local + Market split)
├── requirements.txt
└── pages/
    ├── login.py
    ├── shop_dashboard.py   ← Shop user view
    └── admin_dashboard.py  ← Admin view
```

---

## 🚀 Deploy on Streamlit Community Cloud (Free)

### Step 1 — Put code on GitHub
1. Go to [github.com](https://github.com) → Create free account
2. Create a new repository called `paan-manager` (make it **Public**)
3. Upload all these files keeping the same folder structure

### Step 2 — Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your `paan-manager` repo
5. Set **Main file path** to: `app.py`
6. Click **Deploy** — done! You get a public URL in ~2 minutes

### Step 3 — Share with shops
Give each shop their login:
- Username: shop code in lowercase (e.g. `sam`, `in`, `mg`, `kormangla`)
- Password: code + `123` (e.g. `sam123`, `in123`)
- Admin: `admin` / `admin123`

> **Change passwords first!** Go to database.py and change the seed passwords before deploying.

---

## 🔐 Changing Passwords

In `database.py`, find the seed section and change:
```python
c.execute("INSERT INTO users ...", ("admin", "YOUR_ADMIN_PASSWORD", "admin", None))
```
And for shops:
```python
# Change the password pattern from uname+"123" to whatever you want
c.execute("INSERT INTO users ...", (uname, "YOUR_PASSWORD", "shop", shop))
```

---

## 📱 Features by User

### Shop User (each shop)
- ✅ Enter daily cash + online sales
- ✅ View/set their stock
- ✅ Place restock orders
- ✅ Manage staff (add, salary rate, advances)
- ✅ Mark daily attendance (present/absent)
- ✅ See their own monthly profit/loss

### Admin (you / your dad)
- ✅ All shops overview — sales, profit/loss vs last month
- ✅ All stock across all shops in one view
- ✅ Pending restock orders — preview + fulfill (auto-updates stock)
- ✅ Generate restock PDF — Local items + Market items split (like your existing sheet)
- ✅ All staff salary summary
- ✅ Monthly report per shop

---

## 💡 Notes

- **Database**: SQLite file (`paan_manager.db`) — stored on Streamlit Cloud's filesystem. For persistent data across deploys, upgrade to Supabase (free) later.
- **Salary logic**: Fixed monthly rate ÷ days in month × days present − advances
- **Salary increment**: Add new rate with effective date — old months use old rate automatically
- **Stock update**: When admin fulfills a restock order → stock auto-adds to shop's count
- **PDF**: Splits into Local (🟢) and Market (🔵) sections per shop, with market cost summary

---

## ⚠️ Important: Persistent Database

Streamlit Community Cloud **resets the filesystem** on redeployment. To keep data safe:

**Option A (Quick)**: Export data regularly via the admin panel  
**Option B (Proper)**: Migrate to Supabase free tier
1. Create account at [supabase.com](https://supabase.com)
2. Run the SQL schema from `database.py` in Supabase SQL editor
3. Replace SQLite calls in `database.py` with Supabase client calls

Ask for help with Option B when ready — it's a one-time migration.
