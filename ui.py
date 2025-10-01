import streamlit as st
from config import PDF_PATH, PDF_NAME
import time
import os
import base64
import json

USER_CHAT_FILE = "user_chats.json"

# Load user chats safely
if os.path.exists(USER_CHAT_FILE):
    try:
        with open(USER_CHAT_FILE, "r") as f:
            USER_CHATS = json.load(f)
    except json.JSONDecodeError:
        USER_CHATS = {}
else:
    USER_CHATS = {}

def save_user_chats():
    """Save the current user's chat history + collections to USER_CHATS."""
    if "username" in st.session_state:
        USER_CHATS[st.session_state["username"]] = {
            "pdf_chats": st.session_state.get("pdf_chats", {}),
            "user_collections": st.session_state.get("user_collections", [])
        }
        with open(USER_CHAT_FILE, "w") as f:
            json.dump(USER_CHATS, f)

def load_user_chats():
    """Load the logged-in user's chats + collections into session state."""
    if "username" in st.session_state:
        user_data = USER_CHATS.get(st.session_state["username"], {})
        st.session_state["pdf_chats"] = user_data.get("pdf_chats", {})
        st.session_state["user_collections"] = user_data.get("user_collections", [])
    else:
        st.session_state["pdf_chats"] = {}
        st.session_state["user_collections"] = []


def img_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bot_icon_base64 = img_to_base64("assets/BOTI.png")
user_icon_base64 = img_to_base64("assets/USER.png")

def render_main_ui(send_message):
    # Chat input styling
    st.markdown(
        """
        <style>
        div[data-testid='stChatInput'] {
            max-width: 600px;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False

    selected_pdf = st.session_state.get("selected_pdf")
    pdf_chats = st.session_state.pdf_chats.get(selected_pdf, [])

    # --- Clear chat button ---
    if pdf_chats:
        if st.button("🧹 Clear Chat", key=f"clear_chat_{selected_pdf}"):
            # Clear in session_state
            st.session_state.pdf_chats[selected_pdf] = []
            # Clear in JSON
            if "username" in st.session_state:
                USER_CHATS[st.session_state["username"]][selected_pdf] = []
                with open(USER_CHAT_FILE, "w") as f:
                    json.dump(USER_CHATS, f)
            st.success(f"Chat history for '{selected_pdf}' cleared!")
            st.rerun()

    # --- Show normal chat input if history exists ---
    if pdf_chats:
        show_main_chat_input(send_message, selected_pdf)
        st.session_state.chat_started = True  # mark chat as started
    else:
        # --- Before first message ---
        show_before_message_ui(send_message, selected_pdf)


def show_before_message_ui(send_message, selected_pdf):
    main_container = st.container()
    with main_container:
        st.markdown("""
            <div style='text-align: center; font-size: 20px; padding: 10px 0;'>
                <b>Hi! How can I assist you with your PDF?</b>
            </div>
            """, unsafe_allow_html=True)
    
        st.markdown(
            """
            <style>
            div[data-testid='stChatInput'] {
                max-width: 750px;
                margin: 0 auto;
                text-align:left;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        user_input = st.chat_input("Ask a question...", key=f"before_first_chat_{selected_pdf}")

    # Suggestions pills
    suggestions = [
        "⬇️ Download PDF",
        "📘 What is the summary of the book?",
        "✍️ Who is the author?",
        "💡 What are the key takeaways?",
        "❓ What questions does the book address?"
    ]
    selected_suggestion = st.pills(
        label="Select a suggestion",
        options=suggestions,
        selection_mode="single",
        label_visibility="collapsed"
    )

    # Handle input
    if selected_suggestion:
        st.session_state.input_text = selected_suggestion
        st.session_state.chat_started = True
        send_message()
        save_user_chats()  # <-- Save after user input
        st.rerun()
    elif user_input:
        st.session_state.input_text = user_input
        st.session_state.chat_started = True
        send_message()
        save_user_chats()  # <-- Save after user input
        st.rerun()

def show_main_chat_input(send_message, selected_pdf):
    st.markdown(
        """
        <style>
        div[data-testid='stChatInput'] {
            max-width: 750px;
            margin: 0 auto;
            text-align:left;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    user_input = st.chat_input("Ask a question about the PDF...", key=f"main_chat_input_{selected_pdf}")
    if user_input:
        st.session_state.input_text = user_input
        send_message()
        save_user_chats()  # <-- Save after user input

def setup_ui():
    st.set_page_config(
        page_title="RAG Chatbot",
        page_icon="assets/MYLOGO.png",  
        layout="wide"
    )

    # Load chats for the logged-in user
    if "pdf_chats" not in st.session_state:
        load_user_chats()

    if "input_text" not in st.session_state:
        st.session_state.input_text = ""

    if "pdf_history" not in st.session_state:
        st.session_state.pdf_history = []
    local_pdfs = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
    for pdf in local_pdfs:
        if not any(h["name"] == pdf for h in st.session_state.pdf_history):
            st.session_state.pdf_history.append({"name": pdf, "path": pdf})

# --- The rest of your original render_sidebar, render_chat, typewriter functions remain unchanged ---


def render_sidebar():
    print("[DEBUG] render_sidebar called")
    
    with st.sidebar:
        st.markdown("### 📄 PDF Uploader")
        uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
        if "pdf_history" not in st.session_state:
            st.session_state.pdf_history = []

        if 'user_collections' not in st.session_state:
            st.session_state['user_collections'] = []

        # Handle new upload
        if uploaded_pdf:
            pdf_name = uploaded_pdf.name
            pdf_path = os.path.join(".", pdf_name)
            file_exists = os.path.exists(pdf_path)
            collection_exists = pdf_name in st.session_state['user_collections']

            try:
                if collection_exists and not file_exists:
                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_pdf.read())
                    st.info(f"PDF '{pdf_name}' already indexed. File restored locally.")

                elif file_exists and not collection_exists:
                    st.info(f"File '{pdf_name}' exists locally. Creating embeddings...")
                    from embeddings_utils import build_or_load_index
                    build_or_load_index(pdf_name)
                    st.session_state['user_collections'].append(pdf_name)
                    save_user_chats()

                elif not file_exists and not collection_exists:
                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_pdf.read())
                    st.success(f"Uploaded: {pdf_name}. Now indexing...")
                    from embeddings_utils import build_or_load_index
                    build_or_load_index(pdf_name)
                    st.session_state['user_collections'].append(pdf_name)
                    save_user_chats()

                else:
                    st.info(f"PDF '{pdf_name}' already exists locally and is indexed. Using existing data.")

                st.session_state.selected_pdf = pdf_name
                if not any(pdf['name'] == pdf_name for pdf in st.session_state.pdf_history):
                    st.session_state.pdf_history.append({"name": pdf_name, "path": pdf_path})
                if pdf_name not in st.session_state.pdf_chats:
                    st.session_state.pdf_chats[pdf_name] = []

                save_user_chats()
                if st.session_state.get('selected_pdf') != pdf_name:
                    st.session_state.selected_pdf = pdf_name
                    st.rerun()

            except Exception as e:
                st.warning(f"Error processing PDF: {e}")

        # ✅ Show only this user's collections
        pdf_names = st.session_state['user_collections']

        if pdf_names:
            st.markdown("### 📚 Your Uploaded PDFs")
            for pdf_name in pdf_names:
                col1, col2 = st.columns([4, 1])  # Name + Remove button
                with col1:
                    if st.session_state.get("selected_pdf") == pdf_name:
                        st.markdown(f"**{pdf_name}** ✅")
                    else:
                        if st.button(pdf_name, key=f"select_{pdf_name}"):
                            st.session_state.selected_pdf = pdf_name
                            st.rerun()

                with col2:
                    if st.button("🗑", key=f"remove_{pdf_name}"):
                        # Remove from collections
                        if pdf_name in st.session_state['user_collections']:
                            st.session_state['user_collections'].remove(pdf_name)
    

                        # Remove from pdf_chats
                        if pdf_name in st.session_state['pdf_chats']:
                            del st.session_state['pdf_chats'][pdf_name]

                        # Remove from pdf_history
                        st.session_state['pdf_history'] = [
                            pdf for pdf in st.session_state['pdf_history'] if pdf['name'] != pdf_name
                        ]

                        # Remove from persistent storage
                        save_user_chats()
                        # Reset selected PDF if it's the one being deleted
                        if st.session_state.get("selected_pdf") == pdf_name:
                           st.session_state["selected_pdf"] = None

                        st.success(f"🗑 PDF '{pdf_name}' removed successfully!")
                        st.rerun()
        else:
            st.info("No PDFs uploaded or indexed yet.")




def typewriter(text, delay=0.005):
    """Simulates typing effect with bot icon."""
    container = st.empty()
    displayed_text = ""
    for char in text:
        displayed_text += char
        container.markdown(
            f"""
            <div class='chat-row bot-row'>
                <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center;'>
                <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                </div>
                <div class='chat-bubble bot-msg'>{displayed_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        time.sleep(delay)
    return displayed_text


def render_chat():
    print("[DEBUG] render_chat called")

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 900px;
            margin: 0 auto;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
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
            margin-bottom: 8px; 
        }
        .user-row {
            justify-content: flex-end;
        }
        .user-msg {
            background-color: transparent;
            border: 1px solid #75D677;
            text-align: left;
        }
        .bot-row {
            justify-content: flex-start;
        }
        .bot-msg {
            background-color: transparent;
            text-align: left;
            max-width: 80%;
            border-radius: 10px;
            padding: 8px; 
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected_pdf = st.session_state.get("selected_pdf")
    if not selected_pdf:
        st.warning("⚠️ Please upload or select a PDF to start chatting.")
        return  
    if selected_pdf not in st.session_state.pdf_chats:
        st.session_state.pdf_chats[selected_pdf] = []

    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    chats = st.session_state.pdf_chats[selected_pdf]
    
    for i, chat in enumerate(chats):
        # User message
        st.markdown(
            f"""
            <div class='chat-row user-row'>
                <div class='chat-bubble user-msg'>{chat['user']}</div>
                <div style='width:32px; height:32px; display:flex; align-items:center; justify-content:center;'></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Bot response
        bot_content = chat['bot']
        download_commands = [
            "⬇️ download pdf",
            "download pdf",
            "get pdf",
            "Show pdf",
            "send pdf",
            "download file",
            "get file",
            "send file",
            "pdf download",
            "please download pdf",
            "can i download pdf",
            "download the pdf",
        ]

        if chat['user'].strip().lower() in download_commands:
            pdf_path = next((pdf['path'] for pdf in st.session_state.pdf_history if pdf['name'] == selected_pdf), None)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                bot_content = f"Here is your PDF: <a href='data:application/pdf;base64,{b64_pdf}' download='{selected_pdf}' style='text-decoration:none; font-weight:bold;'>⬇️ {selected_pdf}</a>"
            else:
                bot_content = f"⚠️ Sorry, the PDF <b>{selected_pdf}</b> is not available for download."

            st.markdown(
                f"""
                <div class='chat-row bot-row'>
                    <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center; font-size:18px;'>
                        <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                    </div>
                    <div class='chat-bubble bot-msg'>{bot_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif i == len(chats) - 1 and not chat.get("animated", False):
            final_text = typewriter(bot_content)
            chat['bot'] = final_text
            chat['animated'] = True
        else:
            st.markdown(
                f"""
                <div class='chat-row bot-row'>
                    <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center; font-size:18px;'>
                        <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                    </div>
                    <div class='chat-bubble bot-msg'>{bot_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
