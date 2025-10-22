# ==== ui.py ====

import streamlit as st
import time
import base64
from pymongo import MongoClient
from config import MONGO_URI
# Local-only PDF handling: no Google Drive / OAuth required
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
    with st.sidebar:
        st.markdown("### 📄 Upload a PDF (local only)")
        uploaded_pdf = st.file_uploader("Choose a PDF file to upload", type=["pdf"], key="pdf_uploader")
        upload_clicked = st.button("Upload", key="upload_pdf_button")
        if uploaded_pdf and upload_clicked:
            pdf_name = uploaded_pdf.name
            pdf_bytes = uploaded_pdf.read()

            user_collection_name = f"{username}__{pdf_name}"
            # Check if this PDF already exists in user_collections
            if user_collection_name in st.session_state.get('user_collections', []):
                st.session_state.selected_pdf = pdf_name
                st.session_state.current_collection = user_collection_name
                st.success(f"PDF '{pdf_name}' already exists. Reusing previous chat and collection.", icon="✅")
                st.rerun()

            # Store pdf bytes and metadata in session (local-only)
            if 'pdf_history' not in st.session_state:
                st.session_state['pdf_history'] = []
            st.session_state['pdf_history'].append({
                "name": pdf_name,
                "bytes": pdf_bytes,
                "collection": user_collection_name
            })
            if 'user_collections' not in st.session_state:
                st.session_state['user_collections'] = []
            if user_collection_name not in st.session_state['user_collections']:
                st.session_state['user_collections'].append(user_collection_name)

            # Build embeddings/index for this user's collection using in-memory bytes
            from embeddings_utils import build_or_load_index
            import inspect
            if (
                "vectordb" not in st.session_state
                or st.session_state.vectordb is None
                or st.session_state.PDF_NAME != user_collection_name
            ):
                try:
                    sig = inspect.signature(build_or_load_index)
                    if "pdf_bytes" in sig.parameters:
                        vectordb = build_or_load_index(collection_name=user_collection_name, pdf_bytes=pdf_bytes)
                    else:
                        # Fallback: use embeddings.build_index_from_pdf_bytes if available, then load collection
                        try:
                            from embeddings import build_index_from_pdf_bytes
                            build_index_from_pdf_bytes(pdf_bytes, user_collection_name)
                        except Exception:
                            pass
                        vectordb = build_or_load_index(collection_name=user_collection_name)

                except Exception as e:
                    st.error(f"Failed to build or load PDF index: {e}")
                    return

                if vectordb is None:
                    st.error("Failed to build or load PDF index. Please check your PDF and try again.")
                    return

                st.session_state.vectordb = vectordb
                st.session_state.retriever = vectordb.as_retriever(search_kwargs={"k": 4})
                st.session_state.PDF_NAME = user_collection_name

            st.session_state.selected_pdf = pdf_name
            st.session_state.current_collection = user_collection_name
            if 'pdf_chats' not in st.session_state:
                st.session_state['pdf_chats'] = {}
            st.session_state.pdf_chats[pdf_name] = []
            save_user_chats()
            st.success(f"PDF '{pdf_name}' uploaded and indexed locally!", icon="✅")

        # --- Sidebar PDF list ---
        pdf_names = [
            col.split("__", 1)[1]
            for col in st.session_state.get('user_collections', [])
            if col.startswith(f"{username}__")
        ]

        if pdf_names:
            st.markdown("### 📚 Your Uploaded PDFs (local)")
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

                        # Local-only: remove any stored bytes for this PDF (no Drive delete)
                        # file_bytes entries are stored under 'bytes' in pdf_history
                        file_bytes_entry = next(
                            (pdf for pdf in st.session_state.get('pdf_history', [])
                             if pdf['name'] == pdf_name and pdf.get('collection') == user_collection_name),
                            None
                        )
                        if file_bytes_entry and 'bytes' in file_bytes_entry:
                            # nothing external to delete; just log removal
                            pass

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
    # Find the local stored bytes for the selected PDF
    user_collection_name = st.session_state.get('current_collection')
    file_bytes = None
    if user_collection_name:
        entry = next((pdf for pdf in st.session_state.get('pdf_history', [])
                      if pdf['name'] == selected_pdf and pdf.get('collection') == user_collection_name), None)
        if entry:
            file_bytes = entry.get('bytes')
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

        if i == len(chats) - 1 and not chat.get("animated", False):
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
