import streamlit as st
import json

# === Load secrets from Streamlit ===
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
GDRIVE_SERVICE_ACCOUNT_JSON = st.secrets.get("GDRIVE_SERVICE_ACCOUNT_JSON")
MONGO_URI = st.secrets.get("MONGO_URI")
COLLECTION_NAME = st.secrets.get("COLLECTION_NAME", "default_collection")


# === Parse Google Drive service account JSON ===
try:
	if isinstance(GDRIVE_SERVICE_ACCOUNT_JSON, str):
		GDRIVE_SERVICE_ACCOUNT_DICT = json.loads(GDRIVE_SERVICE_ACCOUNT_JSON)
	elif isinstance(GDRIVE_SERVICE_ACCOUNT_JSON, dict):
		GDRIVE_SERVICE_ACCOUNT_DICT = GDRIVE_SERVICE_ACCOUNT_JSON
	else:
		GDRIVE_SERVICE_ACCOUNT_DICT = None
except Exception as e:
	st.error(f"Error loading GDRIVE_SERVICE_ACCOUNT_JSON: {e}")
	GDRIVE_SERVICE_ACCOUNT_DICT = None
