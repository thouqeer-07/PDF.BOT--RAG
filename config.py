import streamlit as st
import os
from dotenv import load_dotenv

# === Load .env file (optional if using Streamlit Cloud secrets) ===
load_dotenv()

# === API and database configuration ===
QDRANT_URL = st.secrets["QDRANT_URL"]
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
MONGO_URI = st.secrets["MONGO_URI"]
COLLECTION_NAME = st.secrets.get("COLLECTION_NAME", "default_collection")
# Remove Drive file id / OAuth secrets — app runs in local-only, in-memory mode
