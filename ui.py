import streamlit as st
from config import PDF_PATH, PDF_NAME

def setup_ui():
    print("[DEBUG] setup_ui called")
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    st.markdown("<h1 style='text-align:center;color:white;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:white;'>RAG PIPELINE</h4>", unsafe_allow_html=True)
    if "pdf_chats" not in st.session_state:
        st.session_state.pdf_chats = {}
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""
    # Add all local PDFs to pdf_history for download button
    import os
    if "pdf_history" not in st.session_state:
        st.session_state.pdf_history = []
    local_pdfs = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
    for pdf in local_pdfs:
        if not any(h["name"] == pdf for h in st.session_state.pdf_history):
            st.session_state.pdf_history.append({"name": pdf, "path": pdf})

def render_sidebar():
    print("[DEBUG] render_sidebar called")
    with st.sidebar:
        st.markdown("### 📄 PDF Uploader")
        uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
        if "pdf_history" not in st.session_state:
            st.session_state.pdf_history = []
        # Add to history if new upload and not already in Qdrant
        from qdrant_client import QdrantClient
        from config import QDRANT_URL, QDRANT_API_KEY
        if uploaded_pdf:
            pdf_path = uploaded_pdf.name  # Use only the filename as collection name and for local file
            try:
                qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
                existing_collections = [c.name for c in qdrant.get_collections().collections]
                st.session_state.selected_pdf = uploaded_pdf.name
                # Always add to history for download button
                if not any(pdf['name'] == uploaded_pdf.name for pdf in st.session_state.pdf_history):
                    st.session_state.pdf_history.append({"name": uploaded_pdf.name, "path": pdf_path})
                # Initialize chat history for new PDF
                if "pdf_chats" not in st.session_state:
                    st.session_state.pdf_chats = {}
                if uploaded_pdf.name not in st.session_state.pdf_chats:
                    st.session_state.pdf_chats[uploaded_pdf.name] = []
                if uploaded_pdf.name in existing_collections:
                    st.info(f"PDF '{uploaded_pdf.name}' already indexed. Using existing collection.")
                else:
                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_pdf.read())
                    st.success(f"Uploaded: {uploaded_pdf.name}")
                    # Call embedding/indexing immediately after upload for new PDFs
                    from embeddings_utils import build_or_load_index
                    build_or_load_index(uploaded_pdf.name)
                # Only rerun if not already on this PDF to avoid infinite rerun
                if st.session_state.get('selected_pdf') != uploaded_pdf.name:
                    st.session_state.selected_pdf = uploaded_pdf.name
                    st.rerun()
            except Exception as e:
                st.warning(f"Error checking collections: {e}")
        # Show all available collections in Qdrant as PDF history
        try:
            qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            existing_collections = [c.name for c in qdrant.get_collections().collections]
            pdf_names = list(existing_collections)
        except Exception as e:
            st.warning(f"Error fetching collections: {e}")
            pdf_names = [pdf['name'] for pdf in st.session_state.pdf_history]

        if pdf_names:
            # Ensure selected_pdf is in pdf_names, else fallback to first
            current_selected = st.session_state.get("selected_pdf")
            if current_selected not in pdf_names:
                current_selected = pdf_names[0]
                st.session_state.selected_pdf = current_selected
            selected = st.radio("PDF History", pdf_names, index=pdf_names.index(current_selected))
            st.session_state.selected_pdf = selected
        else:
            st.info("No PDFs uploaded or indexed yet.")

def render_chat():
    print("[DEBUG] render_chat called")
    st.markdown(
        """
        <style>
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 70vh;
            overflow-y: auto;
            padding: 12px;
            border-radius: 10px;
        }
        .chat-row {
            display: flex;
            align-items: flex-start;
        }
        .chat-bubble {
            padding: 12px 18px;
            border-radius: 16px;
            max-width: 70%;
            font-size: 15px;
            line-height: 1.4;
            word-wrap: break-word;
        }
        /* User message (right side) */
        .user-row {
            justify-content: flex-end;
        }
        .user-msg {
            background-color: transparent;
            border: 1px solid #4CAF50;
            color: white;
            text-align: left;
        }
        /* Bot message (left side) */
        .bot-row {
            justify-content: flex-start;
        }
        .bot-msg {
            background-color: transparent;
            border: 1px solid  #2196F3;
            color: white;
            text-align: left;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected_pdf = st.session_state.get("selected_pdf")
    if selected_pdf not in st.session_state.pdf_chats:
        st.session_state.pdf_chats[selected_pdf] = []
    # Display PDF name and download button at the top
    st.markdown(f"### 📄 {selected_pdf}")
    pdf_path = next((pdf['path'] for pdf in st.session_state.pdf_history if pdf['name'] == selected_pdf), None)
    if pdf_path:
        with open(pdf_path, "rb") as f:
            st.download_button(
                label=f"Download {selected_pdf}",
                data=f,
                file_name=selected_pdf,
                mime="application/pdf",
            )
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for chat in st.session_state.pdf_chats[selected_pdf]:
        st.markdown(
            f"<div class='chat-row user-row'><div class='chat-bubble user-msg'>{chat['user']}</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='chat-row bot-row'><div class='chat-bubble bot-msg'> {chat['bot']}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)