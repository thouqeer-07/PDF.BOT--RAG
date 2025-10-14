import streamlit as st
import os
from dotenv import load_dotenv

# === Load secrets or .env file ===
load_dotenv()

# === API and database configuration ===
QDRANT_URL = st.secrets("QDRANT_URL")
QDRANT_API_KEY = st.secrets("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets("GOOGLE_API_KEY")
MONGO_URI = st.secrets("MONGO_URI")
COLLECTION_NAME = st.secrets("COLLECTION_NAME", "default_collection")
GOOGLE_CLIENT_ID = st.secrets("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = st.secrets("GOOGLE_CLIENT_SECRET_FILE")
REDIRECT_URI = st.secrets("REDIRECT_URI")
SCOPES = st.secrets("SCOPES")
File=st.secrets("file_id")
OAUTH_PORT = st.secrets("OAUTH_PORT")
# === Google OAuth credentials (for personal Drive) ===
#CLIENT_SECRETS_JSON = os.getenv("CLIENT_SECRETS_JSON")  # path to client_secrets.json
