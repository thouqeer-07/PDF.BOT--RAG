import streamlit as st
import json

# === Load secrets from Streamlit ===
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
GDRIVE_SERVICE_ACCOUNT_JSON = st.secrets.get("GDRIVE_SERVICE_ACCOUNT_JSON")
MONGO_URI = st.secrets.get("MONGO_URI")
COLLECTION_NAME = st.secrets.get("COLLECTION_NAME", "default_collection")

# === No local PDF handling (now cloud-based) ===
PDF_PATH = None
PDF_NAME = None
