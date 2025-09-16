# ==== app.py ====

import streamlit as st
from embeddings_utils import build_or_load_index
from chat_handler import send_message
from ui import setup_ui, render_sidebar, render_chat

print("[DEBUG] Starting app.py")
# 1. UI setup
setup_ui()
print("[DEBUG] UI setup complete")
# 2. Load Qdrant index and retriever
if "vectordb" not in st.session_state or st.session_state.vectordb is None:
    print("[DEBUG] Loading Qdrant index")
    st.session_state.vectordb = build_or_load_index()

retriever = None
if st.session_state.vectordb:
    print("[DEBUG] Creating retriever")
    retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})

# 3. Sidebar
render_sidebar()
print("[DEBUG] Sidebar rendered")
# 4. Chat input and handler
st.text_input("Ask a question about the PDF:", key="input_text", on_change=lambda: send_message(retriever))
print("[DEBUG] Chat input ready")
# 5. Render chat
render_chat()
print("[DEBUG] Chat rendered")
