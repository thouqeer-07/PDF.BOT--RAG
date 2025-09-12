# ==== app.py ====
import os
import pathlib
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# =========================
# 0. ENV
# =========================
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PDF_PATH = "1. Self-Help Author Samuel Smiles.pdf"
PDF_NAME = pathlib.Path(PDF_PATH).name
collection_name = "1. Self-Help Author Samuel Smiles.pdf"

# =========================
# 1. LOAD EXISTING QDRANT INDEX
# =========================
from langchain.embeddings.base import Embeddings
import numpy as np

class DummyEmbeddings(Embeddings):
    """Placeholder embeddings for loading from Qdrant (no API calls)."""
    def __init__(self, dim=768):  # match your stored dimension
        self.dim = dim

    def embed_documents(self, texts):
        return [np.zeros(self.dim).tolist() for _ in texts]

    def embed_query(self, text):
        return np.zeros(self.dim).tolist()


def build_or_load_index(pdf_path):
    """Loads an existing collection from Qdrant without re-embedding."""
    if not QDRANT_URL or not QDRANT_API_KEY:
        st.error("QDRANT_URL or QDRANT_API_KEY not set!")
        return None

    collection_name = "1. Self-Help Author Samuel Smiles.pdf"

    try:
        vectordb = QdrantVectorStore.from_existing_collection(
            collection_name=collection_name,
            location=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            embedding=DummyEmbeddings(dim=768)  # ✅ no API calls
        )
    except Exception as e:
        st.error(f"Failed to load Qdrant index: {e}")
        return None

    return vectordb

# =========================
# 2. PROMPT TEMPLATE
# =========================
SYSTEM_PROMPT = (
    "You are a precise, concise assistant.\n"
    "Answer strictly based on the retrieved context.\n"
    "If the answer is not in the context, say you don't know based on the provided PDF.\n"
)

QA_TEMPLATE = """{system}
# Context:
{context}
# Question:
{question}
# Instructions:
- Answer in 2-5 sentences unless the user asks for more detail.
- Cite the source (page number or filename) if available.
"""

def get_prompt():
    return PromptTemplate(
        template=QA_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )

# =========================
# 3. STREAMLIT UI
# =========================
st.set_page_config(page_title="RAG Chatbot", layout="wide")
st.markdown("<h1 style='text-align:center;color:Gold;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center;color:Brown;'>RAG PIPELINE</h4>", unsafe_allow_html=True)

if "pdf_chats" not in st.session_state:
    st.session_state.pdf_chats = []
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# Load Qdrant index
if "vectordb" not in st.session_state or st.session_state.vectordb is None:
    st.session_state.vectordb = build_or_load_index(PDF_PATH)

retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})

# =========================
# 4. SIDEBAR: PDF VIEWER
# =========================
with st.sidebar:
    st.markdown("### 📄 PDF Viewer")
    if os.path.exists(PDF_PATH):
        st.markdown(f"**File:** {PDF_NAME}")
        with open(PDF_PATH, "rb") as f:
            st.download_button(
                label="📥 Download PDF",
                data=f,
                file_name=PDF_NAME,
                mime="application/pdf"
            )

# =========================
# 5. CHAT HANDLER
# =========================
def send_message():
    user_input = st.session_state.input_text.strip()
    if not user_input:
        return

    greetings = {"hi", "hello", "hey", "hiya", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx"}

    if user_input.lower() in greetings:
        bot_reply = "Hello! 👋 How can I help you today?"
    elif user_input.lower() in farewells:
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif user_input.lower() in thanks:
        bot_reply = "You're welcome! 😊"
    else:
        # Just retrieve docs without metadata display
        docs = retriever.invoke(user_input)
        context = "\n\n".join([d.page_content for d in docs])

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = get_prompt().format(context=context, question=user_input)
        response = model.generate_content(prompt)
        bot_reply = response.text.strip()

    st.session_state.pdf_chats.append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""


# =========================
# 6. RENDER CHAT
# =========================
st.markdown(
    """
    <style>
    .chat-container { display: flex; flex-direction: column; gap: 10px; }
    .chat-bubble { padding: 12px 18px; border-radius: 18px; max-width: 70%;
                   word-wrap: break-word; font-size: 16px; }
    .user-msg { background-color: #4CAF50; color: white; align-self: flex-end;
                text-align: right; margin-left: 30%; }
    .bot-msg { background-color: #E0E0E0; color: black; align-self: flex-start;
               text-align: left; margin-right: 30%; }
    </style>
    """,
    unsafe_allow_html=True
)

st.text_input("Ask a question about the PDF:", key="input_text", on_change=send_message)

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for chat in st.session_state.pdf_chats:
    st.markdown(f"<div class='chat-bubble user-msg'>💬 {chat['user']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chat-bubble bot-msg'>🤖 {chat['bot']}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
