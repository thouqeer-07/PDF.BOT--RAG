

import streamlit as st
import os  # Only for non-file ops
import base64
from pymongo import MongoClient
from ui import load_user_chats, save_user_chats
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY , MONGO_URI
from gdrive_utils import get_drive_service, download_pdf_from_drive

st.set_page_config(
        page_title="RAG Chatbot",
        page_icon="assets/MYLOGO.png",  
        layout="wide"
    )
# --- MongoDB Setup ---

client = MongoClient(MONGO_URI)
db = client["pdfbot"]
users_col = db["users"]
chats_col = db["users"]

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
                    # Reload Google Drive credentials from MongoDB
                    google_creds = user_doc.get("google_creds")
                    google_oauth_data = user_doc.get("google_oauth_data")
                    if google_creds:
                        st.session_state["google_creds"] = google_creds
                    if google_oauth_data:
                        st.session_state["google_oauth_data"] = google_oauth_data
                    st.success(f"🎉 Login successful! Welcome, {user_doc['username']}")
                    load_user_chats()
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

    """Deletes a user's entire account and all associated data."""
    from gdrive_utils import get_or_create_user_folder, list_user_files, delete_pdf_from_drive
    from qdrant_client import QdrantClient

    st.info("🧹 Deleting all your data (MongoDB, Qdrant, and Google Drive)...")

    try:
        # --- Load user data from MongoDB ---
        db = client["pdfbot"]
        users_col = db["users"]  # ✅ This is the actual collection used in your app
        user_data = users_col.find_one({"username": username})

        if not user_data:
            st.warning("User not found in database.")
            return

        user_collections = user_data.get("user_collections", [])
        pdf_history = user_data.get("pdf_history", [])

        # --- 1️⃣ Delete Qdrant Collections ---
        try:
            qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            existing = [c.name for c in qdrant.get_collections().collections]
            for collection in user_collections:
                if collection in existing:
                    qdrant.delete_collection(collection_name=collection)
                    st.info(f"🧾 Deleted Qdrant collection: {collection}")
        except Exception as qe:
            st.warning(f"⚠️ Qdrant deletion error: {qe}")

        # --- 2️⃣ Delete all PDFs from Google Drive ---
        try:
            drive_service = get_drive_service()
            folder_id = get_or_create_user_folder(drive_service, username)
            user_files = list_user_files(drive_service, username)
            for f in user_files:
                try:
                    delete_pdf_from_drive(drive_service, f['id'], username=username)
                    st.info(f"🗑 Deleted PDF: {f['name']}")
                except Exception as de:
                    st.warning(f"⚠️ Failed to delete Drive file {f['name']}: {de}")

            # Delete the folder itself
            try:
                drive_service.files().delete(fileId=folder_id).execute()
                st.info(f"🗂 Deleted Drive folder for user: {username}")
            except Exception as fe:
                st.warning(f"⚠️ Could not delete Drive folder: {fe}")
        except Exception as e:
            st.warning(f"⚠️ Drive deletion error: {e}")

        # --- 3️⃣ Delete from MongoDB ---
        try:
            delete_user(username)
            chats_col.delete_one({"username": username})
            st.info("✅ Removed user and chat data from MongoDB.")
        except Exception as me:
            st.warning(f"⚠️ MongoDB deletion error: {me}")

        # --- 4️⃣ Clear session and confirm ---
        st.session_state.clear()
        st.success("🗑 Account and all related data permanently deleted.")
        st.rerun()

    except Exception as e:
        st.error(f"❌ Unexpected error while deleting account: {e}")


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
                    st.session_state.clear()
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
                     with st.spinner("🧹 Deleting your account and all data... please wait"):
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
