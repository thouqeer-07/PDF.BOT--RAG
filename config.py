import streamlit as st

# === Load secrets from Streamlit ===
QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
MONGO_URI = st.secrets.get("MONGO_URI")
COLLECTION_NAME = st.secrets.get("COLLECTION_NAME", "default_collection")
CLIENT_SECRETS_JSON = st.secrets.get("CLIENT_SECRETS_JSON")