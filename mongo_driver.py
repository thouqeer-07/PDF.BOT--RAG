# mongo_driver.py
from pymongo import MongoClient
from config import MONGO_URI
import streamlit as st

# Initialize MongoDB Client
# We use @st.cache_resource to ensure the connection is created only once per session/run if needed,
# but a simple module-level variable is often enough in Streamlit if not reloading modules constantly.
# However, to avoid issues with Streamlit re-running the script, we can just instantiate it globally.
# Using standard instantiation as seen in previous files.

try:
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    
    # Common collections used across the app
    users_col = db["Test users"]
    chats_col = db["Test users"] # In the original code, chats_col was also db["users"]

    print("[INFO] MongoDB connected successfully.")
except Exception as e:
    print(f"[ERROR] Could not connect to MongoDB: {e}")
    client = None
    db = None
    users_col = None
    chats_col = None
