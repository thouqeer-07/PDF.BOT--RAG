import pathlib
import streamlit as st

QDRANT_URL = st.secrets.get("QDRANT_URL")
QDRANT_API_KEY = st.secrets.get("QDRANT_API_KEY")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

PDF_PATH = next(pathlib.Path(".").glob("*.pdf"), None)
PDF_NAME = pathlib.Path(PDF_PATH).name if PDF_PATH else None
COLLECTION_NAME = "1. Self-Help Author Samuel Smiles.pdf"

print(f"[DEBUG] QDRANT_URL: {QDRANT_URL}")
print(f"[DEBUG] QDRANT_API_KEY: {'set' if QDRANT_API_KEY else 'not set'}")
print(f"[DEBUG] GOOGLE_API_KEY: {'set' if GOOGLE_API_KEY else 'not set'}")
print(f"[DEBUG] PDF_PATH: {PDF_PATH}")
print(f"[DEBUG] PDF_NAME: {PDF_NAME}")
print(f"[DEBUG] COLLECTION_NAME: {COLLECTION_NAME}")