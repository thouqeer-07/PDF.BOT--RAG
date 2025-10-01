import streamlit as st
import json
import os
from ui import load_user_chats, save_user_chats  # <-- import these functions from ui.py

USER_FILE = "users.json"

# Load users safely
if os.path.exists(USER_FILE):
    try:
        with open(USER_FILE, "r") as f:
            USER_DB = json.load(f)
        # Normalize old users (passwords stored as strings)
        for user, data in USER_DB.items():
            if isinstance(data, str):
                USER_DB[user] = {"password": data, "email": ""}
    except json.JSONDecodeError:
        USER_DB = {}
else:
    USER_DB = {}

def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(USER_DB, f)

def login_interface():
    st.markdown("<h3 style='text-align: center;'>👋 Welcome Back!</h3>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center;'>Login</h4>", unsafe_allow_html=True)

    if st.session_state.get("account_created", False):
        st.success("✅ Account created successfully! Please login using your credentials.")
        st.session_state["account_created"] = False

    identifier = st.text_input("Username or Email", key="login_identifier")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", key="login_btn"):
        # Check if identifier matches a username or email
        matched_user = None
        for username, info in USER_DB.items():
            if identifier == username or identifier == info.get("email"):
                matched_user = username
                break

        if matched_user and USER_DB[matched_user]["password"] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = matched_user

            # Load user-specific chat history from user_chats.json
            load_user_chats()

            st.success(f"🎉 Login successful! Welcome, {matched_user}")
            st.rerun()
        else:
            st.error("❌ Invalid username/email or password.")

    if st.button("New User? Create an account", key="goto_create"):
        st.session_state["auth_interface"] = "create_account"
        st.rerun()

def create_account_interface():
    st.markdown("<h3 style='text-align: center;'>📝 Create a New Account</h3>", unsafe_allow_html=True)

    new_user = st.text_input("New Username", key="new_user")
    new_email = st.text_input("Email", key="new_email")
    new_pass = st.text_input("New Password", type="password", key="new_pass")
    confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")

    if st.button("Create Account", key="create_btn"):
        if not new_user or not new_email or not new_pass:
            st.error("Please fill out all fields.")
        elif new_user in USER_DB:
            st.error("Username already exists.")
        elif any(info.get("email") == new_email for info in USER_DB.values()):
            st.error("Email already registered.")
        elif new_pass != confirm_pass:
            st.error("Passwords do not match.")
        else:
            USER_DB[new_user] = {"password": new_pass, "email": new_email}
            save_users()
            st.session_state["account_created"] = True
            st.session_state["auth_interface"] = "login"
            st.rerun()

    if st.button("Already have an account? Login", key="goto_login"):
        st.session_state["auth_interface"] = "login"
        st.rerun()

def require_login():
    if "auth_interface" not in st.session_state:
        st.session_state["auth_interface"] = "login"

    # Sidebar logout button
    with st.sidebar:
        if st.session_state.get("authenticated", False):
            st.markdown(f"**Logged in as:** {st.session_state.get('username')}")
            if st.button("Logout"):
                # Save current user's chat before clearing
                save_user_chats()

                # Clear session state
                st.session_state["authenticated"] = False
                st.session_state["username"] = ""
                st.session_state["pdf_chats"] = {}
                st.session_state["selected_pdf"] = None
                st.success("You have been logged out.")
                st.rerun()

    if not st.session_state.get("authenticated", False):
        if st.session_state["auth_interface"] == "login":
            login_interface()
        else:
            create_account_interface()
        st.stop()
