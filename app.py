import streamlit as st
st.set_page_config(page_title="पान Shop Manager", page_icon="🌿", layout="wide")

from database import init_db
import pages.login as login_page
import pages.shop_dashboard as shop_dash
import pages.admin_dashboard as admin_dash

def main():
    init_db()

    if "user" not in st.session_state:
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.shop_name = None

    if st.session_state.user is None:
        login_page.show()
    elif st.session_state.role == "admin":
        admin_dash.show()
    else:
        shop_dash.show()

main()