import streamlit as st
from database import authenticate


    
def show():
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem 0;'>
        <div style='font-size:3rem'>🌿</div>
        <h1 style='margin:0'>पान Shop Manager</h1>
        <p style='color:gray'>Paan Business Management System</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            st.subheader("Login / लॉगिन")
            username = st.text_input("Username", placeholder="e.g. sam, in, mg, admin")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                user = authenticate(username.strip(), password.strip())
                if user:
                    st.session_state.user = user['username']
                    st.session_state.role = user['role']
                    st.session_state.shop_name = user['shop_name']
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

        st.caption("👆 Shop users: username = shop code (lowercase), password = code + 123  \nAdmin: admin / admin123")
