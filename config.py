import streamlit as st
import os
from dotenv import load_dotenv

# === Load secrets or .env file ===
load_dotenv()

# === API and database configuration ===
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "default_collection")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET_FILE")
REDIRECT_URI = os.getenv("REDIRECT_URI")
# === Google OAuth credentials (for personal Drive) ===
#CLIENT_SECRETS_JSON = os.getenv("CLIENT_SECRETS_JSON")  # path to client_secrets.json
