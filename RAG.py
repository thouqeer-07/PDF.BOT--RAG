import os
import pathlib
import streamlit as st
import google.generativeai as genai
import requests
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.base import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# =========================
# 0. ENV
# =========================
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PDF_PATH = "1. Self-Help Author Samuel Smiles.pdf"
PDF_NAME = pathlib.Path(PDF_PATH).name
collection_name = pathlib.Path(PDF_PATH).stem.replace(" ", "_")

# =========================
# 1. PDF LOADING + CHUNKING
# =========================
def load_doc(path):
    return PyPDFLoader(path).load()

def split_doc(pages):
    splitter = CharacterTextSplitter(
        separator="\n",       # you can also use "" for strict splitting
        chunk_size=500,
        chunk_overlap=100
    )
    return splitter.split_documents(pages)

# =========================
# 2. EMBEDDINGS (Local vs Cloud)
# =========================
import socket
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.embeddings.base import Embeddings
import requests

def is_local():
    try:
        socket.create_connection(("localhost", 11434), timeout=1)
        return True
    except Exception:
        return False

if is_local():
    class OllamaEmbeddings(Embeddings):
        """Local embedding generator using Ollama API"""
        def __init__(self, model="nomic-embed-text", url="http://localhost:11434/api/embed"):
            self.model = model
            self.url = url

        def _get_embedding(self, text):
            r = requests.post(self.url, json={"model": self.model, "input": text})
            r.raise_for_status()
            return r.json()["embeddings"][0]

        def embed_documents(self, texts):
            r = requests.post(self.url, json={"model": self.model, "input": texts})
            r.raise_for_status()
            return r.json()["embeddings"]

        def embed_query(self, text):
            return self._get_embedding(text)
def get_embeddings():
    # Always use Gemini embeddings in Cloud
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# =========================
# 3. BUILD OR LOAD INDEX
# =========================
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

def build_or_load_index(pdf_path, rebuild=False):
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

    embeddings = get_embeddings()  # safe selection

    collection_name = pathlib.Path(pdf_path).stem.replace(" ", "_")

    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embeddings
    )


# =========================
# 4. PROMPT TEMPLATE
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
"""

def get_prompt():
    return PromptTemplate(
        template=QA_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )

# =========================
# 5. STREAMLIT UI
# =========================
st.set_page_config(page_title="RAG Chatbot", layout="wide")
st.markdown("<h1 style='text-align:center;color:Gold;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center;color:Brown;'>RAG PIPELINE</h4>", unsafe_allow_html=True)

if "pdf_chats" not in st.session_state:
    st.session_state.pdf_chats = []
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# Load or build Qdrant index
if "vectordb" not in st.session_state:
    vectordb = build_or_load_index(PDF_PATH, rebuild=False)
    st.session_state.vectordb = vectordb

retriever = st.session_state.vectordb.as_retriever(search_kwargs={"k": 4})
# =========================
# SIDEBAR: PDF VIEWER
# =========================
with st.sidebar:
    st.markdown("### 📄 PDF Viewer")
    if os.path.exists(PDF_PATH):
        # Show file info
        st.markdown(f"**File:** {PDF_NAME}")

        # Option 1: Open PDF in new tab
        with open(PDF_PATH, "rb") as f:
            st.download_button(
                label="📥 Download PDF",
                data=f,
                file_name=PDF_NAME,
                mime="application/pdf"
            )
# =========================
# 6. CHAT HANDLER
# =========================
def send_message():
    user_input = st.session_state.input_text.strip()
    if not user_input:
        return

    # Basic greetings & thanks
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
# 7. RENDER CHAT (Improved UI with visible colors)
# =========================
st.markdown(
    """
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .chat-bubble {
        padding: 12px 18px;
        border-radius: 18px;
        max-width: 70%;
        word-wrap: break-word;
        font-size: 16px;
    }
    .user-msg {
        background-color: #4CAF50;  /* Dark green */
        color: white;
        align-self: flex-end;       /* Align right */
        text-align: right;
        margin-left: 30%;           /* Push further right */
    }
    .bot-msg {
        background-color: #E0E0E0;  /* Light gray */
        color: black;
        align-self: flex-start;      /* Align left */
        text-align: left;
        margin-right: 30%;           /* Optional: push a bit left */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Input box
st.text_input("Ask a question about the PDF:", key="input_text", on_change=send_message)

# Render chat history
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for chat in st.session_state.pdf_chats:
    st.markdown(
        f"<div class='chat-bubble user-msg'>💬 {chat['user']}</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div class='chat-bubble bot-msg'>🤖 {chat['bot']}</div>",
        unsafe_allow_html=True
    )
st.markdown("</div>", unsafe_allow_html=True)


