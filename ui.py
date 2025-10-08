import streamlit as st
import time
import os
import base64
from pymongo import MongoClient
from config import MONGO_URI, GDRIVE_SERVICE_ACCOUNT_DICT
from gdrive_utils import get_drive_service, upload_pdf_to_drive, download_pdf_from_drive
client = MongoClient(MONGO_URI)
db = client["pdfbot"]
chats_col = db["users"]

def save_user_chats():
    """Save the current user's chat history + collections to MongoDB."""
    if "username" in st.session_state:
        username = st.session_state["username"]
        data = {
            "username": username,
            "pdf_chats": st.session_state.get("pdf_chats", {}),
            "user_collections": st.session_state.get("user_collections", [])
        }
        chats_col.update_one({"username": username}, {"$set": data}, upsert=True)


def load_user_chats():
    """Load the logged-in user's chats + collections from MongoDB into session state."""
    if "username" in st.session_state:
        username = st.session_state["username"]
        user_data = chats_col.find_one({"username": username})
        if user_data:
            st.session_state["pdf_chats"] = user_data.get("pdf_chats", {})
            st.session_state["user_collections"] = user_data.get("user_collections", [])
        else:
            st.session_state["pdf_chats"] = {}
            st.session_state["user_collections"] = []
    else:
        st.session_state["pdf_chats"] = {}
        st.session_state["user_collections"] = []


def img_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bot_icon_base64 = img_to_base64("assets/BOTI.png")

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
            if "pdf_chats" in st.session_state:
                st.session_state.pdf_chats[selected_pdf] = []
            # Persist the cleared chat to USER_CHATS
            save_user_chats()
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
        "📘 What is the summary?",
        "✍️ Who is the author?",
        "💡 What are the key takeaways?",
        "❓ What questions does it address?"
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
    print("[DEBUG] setup_ui called")
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    st.markdown("<h1 style='text-align:center;color:white;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;color:white;'>RAG PIPELINE</h4>", unsafe_allow_html=True)
    if "pdf_chats" not in st.session_state:
        st.session_state.pdf_chats = []
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""

    if "pdf_history" not in st.session_state:
        st.session_state.pdf_history = []
    # No local PDF scan; all PDFs are cloud-based

# --- The rest of your original render_sidebar, render_chat, typewriter functions remain unchanged ---


def render_sidebar():
    username = st.session_state.get("username", "anonymous")
    drive_service = get_drive_service(GDRIVE_SERVICE_ACCOUNT_DICT)

    with st.sidebar:
        st.markdown("### 📄 Upload a PDF")
        uploaded_pdf = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader")

        if uploaded_pdf:
            pdf_name = uploaded_pdf.name
            pdf_bytes = uploaded_pdf.read()
            user_collection_name = f"{username}__{pdf_name}"

            # Upload PDF to Google Drive
            upload_result = upload_pdf_to_drive(drive_service, pdf_name, pdf_bytes)
            drive_file_id = upload_result["id"]
            drive_file_link = upload_result["webViewLink"]

            # Save Drive file info in pdf_history
            if 'pdf_history' not in st.session_state:
                st.session_state['pdf_history'] = []
            st.session_state['pdf_history'].append({
                "name": pdf_name,
                "drive_id": drive_file_id,
                "drive_link": drive_file_link,
                "collection": user_collection_name
            })

            # Build embeddings/index for this user's collection
            # Download PDF bytes from Drive and save to temp for PyPDFLoader
            # (PyPDFLoader requires a file path, so we need to save bytes to a temp file)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_pdf_path = tmp_pdf.name

            from embeddings_utils import build_or_load_index
            st.session_state.vectordb = build_or_load_index(collection_name=user_collection_name, pdf_path=tmp_pdf_path)
            st.session_state.retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})

            st.session_state.selected_pdf = pdf_name
            st.session_state.current_collection = user_collection_name

            if 'user_collections' not in st.session_state:
                st.session_state['user_collections'] = []
            st.session_state['user_collections'].append(user_collection_name)

            if 'pdf_chats' not in st.session_state:
                st.session_state['pdf_chats'] = {}
            st.session_state.pdf_chats[pdf_name] = []

            save_user_chats()
            st.success(f"PDF '{pdf_name}' uploaded to Drive and indexed!")
            st.rerun()

        # --- Sidebar PDF list ---
        pdf_names = [pdf['name'] for pdf in st.session_state.get('pdf_history', [])]
        if pdf_names:
            st.markdown("### 📚 Your Uploaded PDFs")
            for pdf in st.session_state.get('pdf_history', []):
                pdf_name = pdf['name']
                drive_file_id = pdf.get('drive_id')
                drive_file_link = pdf.get('drive_link')
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.session_state.get("selected_pdf") == pdf_name:
                        st.markdown(f"**{pdf_name}** ✅ [View in Drive]({drive_file_link})")
                    else:
                        if st.button(pdf_name, key=f"select_{pdf_name}"):
                            st.session_state.selected_pdf = pdf_name
                            st.session_state.current_collection = pdf.get('collection')
                            from embeddings_utils import build_or_load_index
                            # Download PDF from Drive for embedding (if needed)
                            st.session_state.vectordb = build_or_load_index(collection_name=pdf.get('collection'))
                            st.session_state.retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})
                            save_user_chats()
                            st.rerun()
                with col2:
                    if st.button("🗑️", key=f"remove_{pdf_name}"):
                        from qdrant_client import QdrantClient
                        from config import QDRANT_URL, QDRANT_API_KEY
                        user_collection_name = pdf.get('collection')
                        # Delete Qdrant collection
                        if user_collection_name:
                            try:
                                qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
                                collections = qdrant.get_collections().collections
                                collection_names = [c.name for c in collections]
                                if user_collection_name in collection_names:
                                    qdrant.delete_collection(collection_name=user_collection_name)
                            except Exception as e:
                                print(f"[ERROR] Failed to delete Qdrant collection '{user_collection_name}': {e}")
                        # Remove from user_collections
                        if user_collection_name in st.session_state.get('user_collections', []):
                            st.session_state['user_collections'].remove(user_collection_name)
                        # Remove chat history for this PDF from session
                        if pdf_name in st.session_state.get('pdf_chats', {}):
                            del st.session_state['pdf_chats'][pdf_name]
                        # Remove from pdf_history
                        st.session_state['pdf_history'] = [p for p in st.session_state.get('pdf_history', []) if p['name'] != pdf_name]
                        # Remove from MongoDB for this user
                        user_data = chats_col.find_one({"username": username})
                        if user_data:
                            pdf_chats = user_data.get("pdf_chats", {})
                            pdf_chats.pop(pdf_name, None)
                            user_collections = user_data.get("user_collections", [])
                            user_collections = [col for col in user_collections if col != user_collection_name]
                            chats_col.update_one(
                                {"username": username},
                                {"$set": {"pdf_chats": pdf_chats, "user_collections": user_collections}}
                            )
                        if st.session_state.get("selected_pdf") == pdf_name:
                            st.session_state["selected_pdf"] = None
                        st.success(f"PDF '{pdf_name}' fully deleted!", icon="🗑")
                        st.rerun()
        else:
            st.info("No PDFs uploaded or indexed yet.")



def typewriter(text, delay=0.005):
    """Simulates typing effect with bot icon."""
    container = st.empty()
    displayed_text = ""
    fast_delay = 0.001  # much faster typing
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
        time.sleep(fast_delay)
    return displayed_text


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

    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    chats = st.session_state.pdf_chats[selected_pdf]
    # Find the Drive file ID for the selected PDF
    drive_file_id = None
    for pdf in st.session_state.get('pdf_history', []):
        if pdf['name'] == selected_pdf:
            drive_file_id = pdf.get('drive_id')
            break
    drive_service = get_drive_service(GDRIVE_SERVICE_ACCOUNT_DICT)
    for i, chat in enumerate(chats):
        # User message
        st.markdown(
            f"<div class='chat-row user-row'><div class='chat-bubble user-msg'>{chat['user']}</div></div>",
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
            if drive_file_id:
                pdf_bytes = download_pdf_from_drive(drive_service, drive_file_id)
                b64_pdf = base64.b64encode(pdf_bytes).decode()
                bot_content = f"Here is your PDF: <a href='data:application/pdf;base64,{b64_pdf}' download='{selected_pdf}' style='text-decoration:none; font-weight:bold;'>⬇️ {selected_pdf}</a>"
            else:
                bot_content = f"⚠️ Sorry, the PDF <b>{selected_pdf}</b> is not available for download."

            st.markdown(
                f"""
                <div class='chat-row bot-row'>
                    <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center; font-size:18px;' >
                        <img src=\"data:image/png;base64,{bot_icon_base64}\" style=\"width:32px; height:32px;\" />
                    </div>
                    <div class='chat-bubble bot-msg'>{bot_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif i == len(chats) - 1 and not chat.get("animated", False):
            # Show 'Bot is thinking...' interface before typewriter effect
            thinking_container = st.empty()
            thinking_container.markdown(
                f"""
                <div class='chat-row bot-row'>
                    <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center; font-size:18px;' >
                        <img src=\"data:image/png;base64,{bot_icon_base64}\" style=\"width:32px; height:32px;\" />
                    </div>
                    <div class='chat-bubble bot-msg'><i>🤖 Bot is thinking...</i></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            time.sleep(0.7)  # Simulate thinking delay
            thinking_container.empty()
            final_text = typewriter(bot_content)
            chat['bot'] = final_text
            chat['animated'] = True
        else:
            st.markdown(
                f"""
                <div class='chat-row bot-row'>
                    <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center; font-size:18px;' >
                        <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                    </div>
                    <div class='chat-bubble bot-msg'>{bot_content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
