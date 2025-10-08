

import streamlit as st
import os  # Only for non-file ops
import base64
from pymongo import MongoClient
from ui import load_user_chats, save_user_chats
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY , MONGO_URI
from gdrive_utils import get_drive_service, download_pdf_from_drive


# --- MongoDB Setup ---

client = MongoClient(MONGO_URI)
db = client["pdfbot"]
users_col = db["users"]
chats_col = db["user_chats"]

st.set_page_config(layout="wide")


# --- Convert image to base64 ---
def img_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


log_icon_base64 = img_to_base64("assets/LOGIN.png")



# --- MongoDB user DB helper functions ---
def get_user_by_username_or_email(identifier):
    return users_col.find_one({"$or": [{"username": identifier}, {"email": identifier}]})

def get_user_by_username(username):
    return users_col.find_one({"username": username})

def user_exists_by_email(email):
    return users_col.find_one({"email": email}) is not None

def user_exists_by_username(username):
    return users_col.find_one({"username": username}) is not None

def create_user(username, password, email):
    users_col.insert_one({"username": username, "password": password, "email": email})

def delete_user(username):
    users_col.delete_one({"username": username})









# --- LOGIN INTERFACE ---
def login_interface():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>👋 Welcome Back!</h3>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center;'>Login</h4>", unsafe_allow_html=True)

        if st.session_state.get("account_created", False):
            st.success("✅ Account created successfully! Please login using your credentials.")
            st.session_state["account_created"] = False

        identifier = st.text_input("Username or Email", key="login_identifier")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", key="login_btn"):
            user_doc = get_user_by_username_or_email(identifier)
            if user_doc and user_doc.get("password") == password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = user_doc["username"]
                load_user_chats()
                st.success(f"🎉 Login successful! Welcome, {user_doc['username']}")
                st.rerun()
            else:
                st.error("❌ Invalid username/email or password.")

        if st.button("New User? Create an account", key="goto_create"):
            st.session_state["auth_interface"] = "create_account"
            st.rerun()


# --- ACCOUNT CREATION ---
def create_account_interface():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>📝 Create a New Account</h3>", unsafe_allow_html=True)

        new_user = st.text_input("New Username", key="new_user")
        new_email = st.text_input("Email", key="new_email")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")

        if st.button("Create Account", key="create_btn"):
            if not new_user or not new_email or not new_pass:
                st.error("Please fill out all fields.")
            elif user_exists_by_username(new_user):
                st.error("Username already exists.")
            elif user_exists_by_email(new_email):
                st.error("Email already registered.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            else:
                create_user(new_user, new_pass, new_email)
                st.session_state["account_created"] = True
                st.session_state["auth_interface"] = "login"
                st.rerun()

        if st.button("Already have an account? Login", key="goto_login"):
            st.session_state["auth_interface"] = "login"
            st.rerun()


# --- DELETE ACCOUNT FUNCTION ---
def delete_account(username):
    # --- Delete from users collection ---
    delete_user(username)

    # --- Delete from user_chats collection ---
    user_data = chats_col.find_one({"username": username})
    if user_data:
        user_collections = user_data.get("user_collections", [])

        # --- Delete all related Qdrant collections ---
        try:
            qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            collections = qdrant.get_collections().collections
            existing_collections = [c.name for c in collections]
            for col in user_collections:
                if col in existing_collections:
                    qdrant.delete_collection(collection_name=col)
        except Exception as e:
            st.warning(f"⚠️ Error deleting Qdrant data: {e}")

        # --- Delete all PDFs from Google Drive for this user ---
        drive_service = get_drive_service()
        pdf_history = user_data.get("pdf_history", [])
        for pdf in pdf_history:
            file_id = pdf.get("file_id")
            if file_id:
                try:
                    drive_service.files().delete(fileId=file_id).execute()
                except Exception as e:
                    st.warning(f"⚠️ Could not delete PDF from Drive: {e}")

        # Remove user chat document
        chats_col.delete_one({"username": username})

    # --- Clear session ---
    st.session_state.clear()
    st.success("🗑 Your account and all data have been permanently deleted.")
    st.rerun()


# --- REQUIRE LOGIN + SIDEBAR SETTINGS ---
def require_login():
    if "auth_interface" not in st.session_state:
        st.session_state["auth_interface"] = "login"

    with st.sidebar:
        if st.session_state.get("authenticated", False):
            username = st.session_state.get("username", "anonymous")
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 10px;">
                    <img src="data:image/png;base64,{log_icon_base64}" width="30" height="30" style="border-radius:10%;" />
                    <span><b>{username}</b></span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # --- Settings checkbox ---
            show_settings = st.checkbox("⚙️ Settings")

            if show_settings:

                # Logout button
                if st.button("🚪 Logout"):
                    save_user_chats()
                    st.session_state["authenticated"] = False
                    st.session_state["username"] = ""
                    st.session_state["pdf_chats"] = {}
                    st.session_state["selected_pdf"] = None
                    st.success("You have been logged out.")
                    st.rerun()


                # --- Delete Account Section ---
                if "confirm_delete" not in st.session_state:
                    st.session_state["confirm_delete"] = False

                if not st.session_state["confirm_delete"]:
                    if st.button("Delete Account", type="primary"):
                        st.session_state["confirm_delete"] = True
                        st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to permanently delete your account and all data?")
                    action = st.pills(
                        label="Confirm delete?",
                        options=["✅ Yes, delete permanently", "❌ Cancel"],
                        selection_mode="single",
                        label_visibility="collapsed"
                    )
                    if action == "✅ Yes, delete permanently":
                        delete_account(username)
                    elif action == "❌ Cancel":
                        st.session_state["confirm_delete"] = False
                        st.rerun()

    # --- Login / Create account interfaces ---
    if not st.session_state.get("authenticated", False):
        if st.session_state["auth_interface"] == "login":
            login_interface()
        else:
            create_account_interface()
        st.stop()
