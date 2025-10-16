# ==== ui.py ====

import streamlit as st
import time
import base64
import html as _html
import re
from pymongo import MongoClient
from config import MONGO_URI
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
            "user_collections": st.session_state.get("user_collections", []),
            "pdf_history": st.session_state.get("pdf_history", [])
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
            st.session_state["pdf_history"] = user_data.get("pdf_history", [])
            # Restore selected_pdf and current_collection if possible
            if st.session_state["user_collections"]:
                # Only restore selected_pdf if it was previously set
                prev_selected = user_data.get("selected_pdf")
                if prev_selected and any(prev_selected in c for c in st.session_state["user_collections"]):
                    st.session_state["selected_pdf"] = prev_selected
                    st.session_state["current_collection"] = next((c for c in st.session_state["user_collections"] if prev_selected in c), None)
                else:
                    st.session_state["selected_pdf"] = None
                    st.session_state["current_collection"] = None
            st.session_state["chat_started"] = False
        else:
            st.session_state["pdf_chats"] = {}
            st.session_state["user_collections"] = []
            st.session_state["pdf_history"] = []
            st.session_state["selected_pdf"] = None
            st.session_state["current_collection"] = None
    else:
        st.session_state["pdf_chats"] = {}
        st.session_state["user_collections"] = []
        st.session_state["pdf_history"] = []
        st.session_state["selected_pdf"] = None
        st.session_state["current_collection"] = None


def img_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bot_icon_base64 = img_to_base64("assets/BOTI.png")


def sanitize_html(text: str) -> str:
    """Sanitize LLM-generated HTML while allowing a small whitelist of tags.

    Strategy:
    - Escape the full text, then selectively unescape only allowed tags.
    - Allow <strong>, <em>, <p>, <br>, <ul>, <li>, and <a href="..."> with http/data/mailto schemes.
    - Any other angle brackets are kept escaped to avoid createElement errors.
    """
    if text is None:
        return ""
    # Fully escape first to neutralize any tags
    escaped = _html.escape(text)

    # Helper list of allowed simple tags
    allowed_simple = ["strong", "em", "p", "br", "ul", "li"]
    for tag in allowed_simple:
        # unescape opening and closing tags; handle self-closing br
        escaped = re.sub(rf'&lt;{tag}&gt;', f'<{tag}>', escaped, flags=re.IGNORECASE)
        escaped = re.sub(rf'&lt;/{tag}&gt;', f'</{tag}>', escaped, flags=re.IGNORECASE)
        if tag == 'br':
            escaped = re.sub(rf'&lt;{tag}\s*/&gt;', f'<{tag}/>', escaped, flags=re.IGNORECASE)

    # Unescape <a href='...'> and </a> but only for safe href schemes
    def _restore_a(match):
        href = match.group(1)
        text_inside = match.group(2)
        # Only allow safe schemes
        if href.startswith('http://') or href.startswith('https://') or href.startswith('data:') or href.startswith('mailto:'):
            href_unq = href.replace('&quot;', '"').replace('&#x27;', "'")
            return f'<a href="{href_unq}">{text_inside}</a>'
        # otherwise return escaped representation (keep it safe)
        return f'&lt;a href=&quot;{href}&quot;&gt;{text_inside}&lt;/a&gt;'

    # Pattern: &lt;a href=&quot;...&quot;&gt;...&lt;/a&gt;
    escaped = re.sub(r'&lt;a href=(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;)&gt;(.*?)&lt;/a&gt;', _restore_a, escaped, flags=re.IGNORECASE | re.DOTALL)

    # Ensure any remaining literal < or > are escaped
    escaped = escaped.replace('<', '&lt;').replace('>', '&gt;')

    # Restore allowed simple tags back from escaped form
    for tag in allowed_simple:
        escaped = escaped.replace(f'&lt;{tag}&gt;', f'<{tag}>')
        escaped = escaped.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
        if tag == 'br':
            escaped = escaped.replace(f'&lt;{tag}/&gt;', f'<{tag}/>')

    return escaped

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
        if not selected_pdf:
            st.error("Please select or upload a PDF before sending a message.")
            return
        st.session_state.input_text = selected_suggestion
        st.session_state.chat_started = True
        send_message()
        save_user_chats()  # <-- Save after user input
        st.rerun()
    elif user_input:
        if not selected_pdf:
            st.error("Please select or upload a PDF before sending a message.")
            return
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
        if not selected_pdf:
            st.error("Please select or upload a PDF before sending a message.")
            return
        st.session_state.input_text = user_input
        send_message()
        save_user_chats()  # <-- Save after user input

def setup_ui():
    st.set_page_config(
        page_title="PDF Chatbot",
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
    # No local PDF scan; all PDFs are cloud-based

# --- The rest of your original render_sidebar, render_chat, typewriter functions remain unchanged ---


def render_sidebar():
    username = st.session_state.get("username", "guest")
    # Ensure MongoDB collection handle is always available
    from pymongo import MongoClient
    from config import MONGO_URI
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    chats_col = db["users"]
    creds_ok = False
    drive_service = None
    # Check for Google Drive credentials
    if "google_creds" in st.session_state:
        creds_ok = True
    else:
        # Try to load from MongoDB
        from pymongo import MongoClient
        from config import MONGO_URI
        client = MongoClient(MONGO_URI)
        db = client["pdfbot"]
        chats_col = db["users"]
        user_data = chats_col.find_one({"username": username})
        if user_data and user_data.get("google_creds"):
            st.session_state["google_creds"] = user_data["google_creds"]
            creds_ok = True
    if creds_ok:
        try:
            drive_service = get_drive_service()
        except Exception as e:
            st.error(f"Google Drive authentication failed: {e}. Please reconnect.")
            creds_ok = False

    with st.sidebar:
        st.markdown("### 📄 Upload a PDF")
        if not creds_ok:
            st.warning("Google Drive not connected. Please connect to upload/download files.")
            # Show only the Connect to Google Drive link
            import json
            from google_auth_oauthlib.flow import Flow
            from config import REDIRECT_URI, SCOPES
            client_config = json.loads(st.secrets["GOOGLE_CLIENT_SECRET_FILE"])
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt="consent", state=username)
            st.markdown(f"### 🔗 [Connect to Google Drive]({auth_url})")
        else:
            uploaded_pdf = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader")
            upload_clicked = st.button("Upload", key="upload_pdf_button")
            if uploaded_pdf and upload_clicked:
                pdf_name = uploaded_pdf.name
                pdf_bytes = uploaded_pdf.read()
                # Upload to Google Drive in user's folder (will reuse if exists)
                drive_result = upload_pdf_to_drive(drive_service, pdf_name, pdf_bytes, username=username)
                file_id = drive_result["id"]
                webViewLink = drive_result["webViewLink"]

                user_collection_name = f"{username}__{pdf_name}"
                # Check if this PDF already exists in user_collections
                if user_collection_name in st.session_state.get('user_collections', []):
                    # Reuse existing chat interface and collection
                    st.session_state.selected_pdf = pdf_name
                    st.session_state.current_collection = user_collection_name
        
                    st.success(f"PDF '{pdf_name}' already exists. Reusing previous chat and collection.", icon="✅")
                    st.rerun()
                else:
                    # Store file_id in pdf_history and user_collections
                    if 'pdf_history' not in st.session_state:
                        st.session_state['pdf_history'] = []
                    st.session_state['pdf_history'].append({
                        "name": pdf_name,
                        "file_id": file_id,
                        "webViewLink": webViewLink,
                        "collection": user_collection_name
                    })
                    if 'user_collections' not in st.session_state:
                        st.session_state['user_collections'] = []
                    if user_collection_name not in st.session_state['user_collections']:
                        st.session_state['user_collections'].append(user_collection_name)

                    # Build embeddings/index for this user's collection using in-memory bytes
                    from embeddings_utils import build_or_load_index
                    import tempfile
                    import os
                    # Only build embeddings if not already present for this collection
                    if (
                        "vectordb" not in st.session_state
                        or st.session_state.vectordb is None
                        or st.session_state.PDF_NAME != user_collection_name
                    ):
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                            tmp.write(pdf_bytes)
                            tmp.flush()
                            temp_pdf_path = tmp.name
                        try:
                            vectordb = build_or_load_index(collection_name=user_collection_name, pdf_path=temp_pdf_path)
                            if vectordb is None:
                                st.error("Failed to build or load PDF index. Please check your PDF and try again.")
                                return
                            st.session_state.vectordb = vectordb
                            st.session_state.retriever = vectordb.as_retriever(search_kwargs={"k": 4})
                            st.session_state.PDF_NAME = user_collection_name
                        finally:
                            try:
                                os.remove(temp_pdf_path)
                            except Exception as e:
                                print(f"[WARNING] Could not delete temp PDF file: {e}")

                    st.session_state.selected_pdf = pdf_name
                    st.session_state.current_collection = user_collection_name
                    if 'pdf_chats' not in st.session_state:
                        st.session_state['pdf_chats'] = {}
                    st.session_state.pdf_chats[pdf_name] = []
                    save_user_chats()
                    st.success(f"PDF '{pdf_name}' uploaded to Drive and indexed!", icon="✅")
                if 'pdf_history' not in st.session_state:
                    st.session_state['pdf_history'] = []
                st.session_state['pdf_history'].append({
                    "name": pdf_name,
                    "file_id": file_id,
                    "webViewLink": webViewLink,
                    "collection": user_collection_name
                })
                if 'user_collections' not in st.session_state:
                    st.session_state['user_collections'] = []
                if user_collection_name not in st.session_state['user_collections']:
                    st.session_state['user_collections'].append(user_collection_name)

                # Build embeddings/index for this user's collection using in-memory bytes
                from embeddings_utils import build_or_load_index
                import tempfile
                import os
                # Only build embeddings if not already present for this collection
                if (
                    "vectordb" not in st.session_state
                    or st.session_state.vectordb is None
                    or st.session_state.PDF_NAME != user_collection_name
                ):
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(pdf_bytes)
                        tmp.flush()
                        temp_pdf_path = tmp.name
                    try:
                        vectordb = build_or_load_index(collection_name=user_collection_name, pdf_path=temp_pdf_path)
                        if vectordb is None:
                            st.error("Failed to build or load PDF index. Please check your PDF and try again.")
                            return
                        st.session_state.vectordb = vectordb
                        st.session_state.retriever = vectordb.as_retriever(search_kwargs={"k": 4})
                        st.session_state.PDF_NAME = user_collection_name
                    finally:
                        try:
                            os.remove(temp_pdf_path)
                        except Exception as e:
                            print(f"[WARNING] Could not delete temp PDF file: {e}")

                st.session_state.selected_pdf = pdf_name
                st.session_state.current_collection = user_collection_name
                if 'pdf_chats' not in st.session_state:
                    st.session_state['pdf_chats'] = {}
                st.session_state.pdf_chats[pdf_name] = []
                save_user_chats()
                st.success(f"PDF '{pdf_name}' uploaded to Drive and indexed!", icon="✅")

        # --- Sidebar PDF list ---
        pdf_names = [
            col.split("__", 1)[1]
            for col in st.session_state.get('user_collections', [])
            if col.startswith(f"{username}__")
        ]

        if pdf_names:
            st.markdown("### 📚 Your Uploaded PDFs")
            for i, pdf_name in enumerate(pdf_names):
                user_collection_name = next(
                    (col for col in st.session_state['user_collections']
                     if col.startswith(f"{username}__{pdf_name}")),
                    None
                )
                col1, col2 = st.columns([4, 2])
                with col1:
                    if st.session_state.get("selected_pdf") == pdf_name:
                        st.markdown(f"**{pdf_name}** ✅")
                    else:
                        if st.button(pdf_name, key=f"select_{pdf_name}"):
                            if user_collection_name:
                                st.session_state.current_collection = user_collection_name
                                from embeddings_utils import build_or_load_index
                                st.session_state.vectordb = build_or_load_index(collection_name=user_collection_name)
                                st.session_state.retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})

                            if 'pdf_chats' not in st.session_state:
                                st.session_state['pdf_chats'] = {}
                            if pdf_name not in st.session_state.pdf_chats:
                                # try to restore from persisted MongoDB if available
                                user_data = chats_col.find_one({"username": username})
                                restored_chats = user_data.get("pdf_chats", {}).get(pdf_name, []) if user_data else []
                                st.session_state.pdf_chats[pdf_name] = restored_chats if restored_chats is not None else []

                            st.session_state.selected_pdf = pdf_name
                            # Persist selection so reload preserves the correct chat mapping
                            save_user_chats()
                            st.rerun()

                with col2:
                    if st.button("🗑️", key=f"remove_{user_collection_name}_{pdf_name}_{i}"):
                        from qdrant_client import QdrantClient
                        from config import QDRANT_URL, QDRANT_API_KEY

                        # Delete Qdrant collection
                        if user_collection_name:
                            try:
                                qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
                                collections = qdrant.get_collections().collections
                                collection_names = [c.name for c in collections]
                                if user_collection_name in collection_names:
                                    qdrant.delete_collection(collection_name=user_collection_name)
                                    import time as _time
                                    for _ in range(5):
                                        collections = qdrant.get_collections().collections
                                        collection_names = [c.name for c in collections]
                                        if user_collection_name not in collection_names:
                                            break
                                        _time.sleep(0.5)
                            except Exception as e:
                                print(f"[ERROR] Failed to delete Qdrant collection '{user_collection_name}': {e}")

                        # Delete PDF from Google Drive
                        file_id = next(
                            (pdf['file_id'] for pdf in st.session_state.get('pdf_history', [])
                             if pdf['name'] == pdf_name and pdf.get('collection') == user_collection_name),
                            None
                        )
                        if file_id:
                            try:
                                from gdrive_utils import delete_pdf_from_drive
                                delete_pdf_from_drive(drive_service, file_id, username=username)
                            except Exception as e:
                                print(f"[ERROR] Failed to delete PDF from Drive: {e}")

                        # Remove from user_collections
                        if user_collection_name in st.session_state.get('user_collections', []):
                            st.session_state['user_collections'].remove(user_collection_name)

                        # Remove chat history for this PDF from session
                        if pdf_name in st.session_state.get('pdf_chats', {}):
                            del st.session_state['pdf_chats'][pdf_name]

                        # Remove from pdf_history
                        st.session_state['pdf_history'] = [
                            pdf for pdf in st.session_state.get('pdf_history', [])
                            if not (pdf['name'] == pdf_name and pdf.get('collection') == user_collection_name)
                        ]

                        # Remove from MongoDB for this user
                        user_data = chats_col.find_one({"username": username})
                        if user_data:
                            pdf_chats = user_data.get("pdf_chats", {})
                            pdf_chats.pop(pdf_name, None)
                            user_collections = user_data.get("user_collections", [])
                            user_collections = [col for col in user_collections if col != user_collection_name]
                            pdf_history = user_data.get("pdf_history", [])
                            pdf_history = [pdf for pdf in pdf_history if not (pdf['name'] == pdf_name and pdf.get('collection') == user_collection_name)]
                            chats_col.update_one(
                                {"username": username},
                                {"$set": {"pdf_chats": pdf_chats, "user_collections": user_collections, "pdf_history": pdf_history}}
                            )

                        if st.session_state.get("selected_pdf") == pdf_name:
                            st.session_state["selected_pdf"] = None
                        st.success("🗑 PDF deleted!")
                        st.rerun()
        else:
            st.info("No PDFs uploaded or indexed yet.")



def typewriter(text, delay=0.005):
    """Simulates typing effect with bot icon.

    If the text contains HTML, sanitize and render the entire HTML atomically to avoid partial-tag DOM errors.
    For plain text, display with a typing effect (escaped to avoid accidental tags).
    """
    container = st.empty()
    # If text contains HTML-like characters, treat as HTML and render sanitized HTML atomically
    if "<" in (text or "") and ">" in (text or ""):
        sanitized = sanitize_html(text)
        container.markdown(
            f"""
            <div class='chat-row bot-row'>
                <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center;'>
                <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                </div>
                <div class='chat-bubble bot-msg'>{sanitized}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Return plain text fallback (tags removed) for storage in chat['bot']
        return _html.unescape(re.sub(r'<[^>]+>', '', sanitized))

    # Plain text path with typing effect (escape to avoid any accidental tags)
    displayed_text = ""
    fast_delay = 0.001  # much faster typing
    for char in text:
        displayed_text += char
        safe = _html.escape(displayed_text)
        container.markdown(
            f"""
            <div class='chat-row bot-row'>
                <div style='width:32px; height:32px; display:flex; text-align:left; align-items:center; justify-content:center;'>
                <img src="data:image/png;base64,{bot_icon_base64}" style="width:32px; height:32px;" />
                </div>
                <div class='chat-bubble bot-msg'>{safe}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(fast_delay)
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
    # Find the Google Drive file ID for the selected PDF
    user_collection_name = st.session_state.get('current_collection')
    file_id = None
    if user_collection_name:
        file_id = next((pdf['file_id'] for pdf in st.session_state.get('pdf_history', [])
                        if pdf['name'] == selected_pdf and pdf.get('collection') == user_collection_name), None)
    drive_service = get_drive_service()
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
            if file_id:
                from gdrive_utils import download_pdf_from_drive
                username = st.session_state.get("username", "guest")
                try:
                    pdf_bytes = download_pdf_from_drive(drive_service, file_id, username=username)
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                    bot_content = f"Here is your PDF: <a href='data:application/pdf;base64,{b64_pdf}' download='{selected_pdf}' style='text-decoration:none; font-weight:bold;'>⬇️ {selected_pdf}</a>"
                except Exception as e:
                    bot_content = f"⚠️ Sorry, the PDF <b>{selected_pdf}</b> could not be downloaded: {e}"
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
