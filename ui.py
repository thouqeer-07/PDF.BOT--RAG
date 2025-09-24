import streamlit as st
from config import PDF_PATH, PDF_NAME

def setup_ui():
    print("[DEBUG] setup_ui called")
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    st.markdown("<h1 style='text-align:center;color:white;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:white;'>RAG PIPELINE</h4>", unsafe_allow_html=True)
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
            background-color: #E0E0E0;
            color: black;
            align-self: flex-start;
            text-align: left;
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
