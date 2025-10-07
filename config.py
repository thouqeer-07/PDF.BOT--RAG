import streamlit as st
import pathlib
import json
import base64

# === Load secrets from Streamlit ===
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
GDRIVE_SERVICE_ACCOUNT_JSON = st.secrets.get("GDRIVE_SERVICE_ACCOUNT_JSON")
MONGO_URI = st.secrets.get("MONGO_URI")
COLLECTION_NAME = st.secrets.get("COLLECTION_NAME", "default_collection")

# === Handle PDF path ===
PDF_PATH = next(pathlib.Path(".").glob("*.pdf"), None)
PDF_NAME = pathlib.Path(PDF_PATH).name if PDF_PATH else None

# === Debug prints ===
st.write(f"[DEBUG] GDRIVE_SERVICE_ACCOUNT_JSON: {'set' if GDRIVE_SERVICE_ACCOUNT_JSON else 'not set'}")
st.write(f"[DEBUG] MONGO_URI: {'set' if MONGO_URI else 'not set'}")
st.write(f"[DEBUG] QDRANT_API_KEY: {'set' if QDRANT_API_KEY else 'not set'}")
st.write(f"[DEBUG] GOOGLE_API_KEY: {'set' if GOOGLE_API_KEY else 'not set'}")
st.write(f"[DEBUG] PDF_PATH: {PDF_PATH}")
st.write(f"[DEBUG] PDF_NAME: {PDF_NAME}")
