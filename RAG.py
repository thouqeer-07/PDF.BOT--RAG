import os
import pathlib
import streamlit as st
import google.generativeai as genai
import requests
import numpy as np
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.base import Embeddings
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

# =========================
# 0. ENV + GLOBALS
# =========================
load_dotenv()
INDEX_DIR = pathlib.Path("./index")
INDEX_DIR.mkdir(exist_ok=True)

QDRANT_URL = os.getenv("QDRANT_URL")   
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Hard-coded PDF path (your file)
PDF_PATH = "1. Self-Help Author Samuel Smiles.pdf"
PDF_NAME = pathlib.Path(PDF_PATH).name

# =========================
# 1. DOC LOADING + SPLITTING
# =========================
def load_doc(path):
    return PyPDFLoader(path).load()

def split_doc(pages):
    return RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(pages)

# =========================
# 2. OLLAMA EMBEDDINGS
# =========================
class OllamaEmbeddings(Embeddings):
    def __init__(self, model="nomic-embed-text", url="http://localhost:11434/api/embed"):
        self.model = model
        self.url = url

    def _get_embedding(self, text):
        r = requests.post(self.url, json={"model": self.model, "input": text})
        if r.status_code == 200 and "embeddings" in r.json():
            return r.json()["embeddings"][0]
        raise RuntimeError(f"Ollama API error {r.status_code}: {r.text}")

    def embed_documents(self, texts):
        r = requests.post(self.url, json={"model": self.model, "input": texts})
        if r.status_code == 200 and "embeddings" in r.json():
            return r.json()["embeddings"]
        raise RuntimeError(f"Ollama API error {r.status_code}: {r.text}")    
    def embed_query(self, text):
        return self._get_embedding(text)

# =========================
# 3. BUILD OR LOAD INDEX (QDRANT CLOUD)
# =========================
def build_or_load_index(pdf_path, rebuild=False):
    collection_name = pathlib.Path(pdf_path).stem.replace(" ", "_")

    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embeddings = OllamaEmbeddings()

    # Reuse collection if already exists
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if not rebuild and collection_name in collections:
        return Qdrant(client=qdrant_client, collection_name=collection_name, embeddings=embeddings)

    # Otherwise, load and embed
    pages = load_doc(pdf_path)
    chunks = split_doc(pages)

    return Qdrant.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
    )

# =========================
# 4. PROMPT
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
    st.session_state.pdf_chats = {}
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "vectorstores" not in st.session_state:
    st.session_state.vectorstores = {}
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# Always load your hard-coded PDF
if PDF_NAME not in st.session_state.vectorstores:
    vectordb = build_or_load_index(PDF_PATH, rebuild=False)
    st.session_state.vectorstores[PDF_NAME] = vectordb
    st.session_state.pdf_chats[PDF_NAME] = []

st.session_state.selected_pdf = PDF_NAME
st.sidebar.success(f"✅ {PDF_NAME} loaded!")

# =========================
# 6. CHAT HANDLER
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
        vectordb = st.session_state.vectorstores[st.session_state.selected_pdf]
        retriever = vectordb.as_retriever(search_kwargs={"k": 4})

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash")

        with st.spinner("🤖 Thinking..."):
            docs = retriever.get_relevant_documents(user_input)
            context = "\n\n".join([d.page_content for d in docs])
            prompt = get_prompt().format(context=context, question=user_input)
            response = model.generate_content(prompt)
            bot_reply = response.text.strip()

    st.session_state.pdf_chats[st.session_state.selected_pdf].append(
        {"role": "user", "content": user_input}
    )
    st.session_state.pdf_chats[st.session_state.selected_pdf].append(
        {"role": "assistant", "content": bot_reply}
    )
    st.session_state.input_text = ""

# =========================
# 7. RENDER CHAT
# =========================
if st.session_state.selected_pdf:
    name = st.session_state.selected_pdf
    st.markdown(f"<h3 style='color:purple;'>Chat Interface - {name}</h3>", unsafe_allow_html=True)
    chat = st.session_state.pdf_chats[name]

    for msg in chat:
        if msg["role"] == "user":
            st.markdown(
                f"<div style='display:flex;justify-content:flex-end;margin:5px 0;'>"
                f"<div style='background-color:lightblue;color:#000;padding:12px;border-radius:12px;max-width:70%;"
                f"font-size:16px;line-height:1.5;word-wrap:break-word;'>{msg['content']}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='display:flex;justify-content:flex-start;margin:5px 0;'>"
                f"<div style='background-color:#F1F0F0;color:#000;padding:12px;border-radius:12px;max-width:70%;"
                f"font-size:16px;line-height:1.5;word-wrap:break-word;'>{msg['content']}</div></div>",
                unsafe_allow_html=True,
            )

    st.text_input("Type your question here...", key="input_text", on_change=send_message)
