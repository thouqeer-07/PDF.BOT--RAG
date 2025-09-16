import streamlit as st
from config import PDF_PATH, PDF_NAME

def setup_ui():
    print("[DEBUG] setup_ui called")
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    st.markdown("<h1 style='text-align:center;color:Gold;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:Brown;'>RAG PIPELINE</h4>", unsafe_allow_html=True)
    if "pdf_chats" not in st.session_state:
        st.session_state.pdf_chats = []
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""

def render_sidebar():
    print("[DEBUG] render_sidebar called")
    with st.sidebar:
        st.markdown("### 📄 PDF Viewer")
        if PDF_PATH:
            import os
            if os.path.exists(PDF_PATH):
                st.markdown(f"**File:** {PDF_NAME}")
                with open(PDF_PATH, "rb") as f:
                    st.download_button(
                        label="📥 Download PDF",
                        data=f,
                        file_name=PDF_NAME,
                        mime="application/pdf",
                    )
            else:
                st.warning("No PDF file found in project directory!")

def render_chat():
    print("[DEBUG] render_chat called")
    st.markdown(
        """
        <style>
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .chat-bubble {
            padding: 12px 18px;
            border-radius: 18px;
            max-width: 70%;
            word-wrap: break-word;
            font-size: 16px;
        }
        .user-msg {
            background-color: #4CAF50;
            color: white;
            align-self: flex-end;
            text-align: right;
            margin-left: 30%;
        }
        .bot-msg {
            background-color: #E0E0E0;
            color: black;
            align-self: flex-start;
            text-align: left;
            margin-right: 30%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for chat in st.session_state.pdf_chats:
        st.markdown(f"<div class='chat-bubble user-msg'>💬 {chat['user']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chat-bubble bot-msg'>🤖 {chat['bot']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
