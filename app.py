# ==== app.py ====
import streamlit as st
from embeddings_utils import build_or_load_index
from chat_handler import send_message
import ui
from ui import setup_ui, render_sidebar, render_chat, render_main_ui
print("[DEBUG] Starting app.py")
from auth import require_login
require_login()

# 1. UI setup
setup_ui()
print("[DEBUG] UI setup complete")

# 2. Handle PDF selection and build index
selected_pdf = st.session_state.get("selected_pdf", None)
if selected_pdf:
    # Always use the exact filename as the collection name
    collection_name = selected_pdf
    print(f"[DEBUG] Using Qdrant collection for selected PDF: {collection_name}")
    st.session_state.vectordb = build_or_load_index(collection_name)
    st.session_state.PDF_NAME = collection_name
    # Always rebuild retriever for selected collection
    if st.session_state.vectordb:
        print("[DEBUG] Creating retriever for selected PDF")
        st.session_state.retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})
else:
    if "vectordb" not in st.session_state or st.session_state.vectordb is None:
        print("[DEBUG] Loading Qdrant index for default PDF")
        st.session_state.vectordb = build_or_load_index()
    st.session_state.PDF_NAME = None
    if st.session_state.vectordb:
        print("[DEBUG] Creating retriever for default PDF")
        st.session_state.retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})

# 3. Sidebar
render_sidebar()
print("[DEBUG] Sidebar rendered")
ui.render_main_ui(send_message)
render_chat()
print("[DEBUG] Chat rendered")

