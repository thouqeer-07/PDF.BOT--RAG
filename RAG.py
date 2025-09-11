import os
import pathlib
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# =========================
# 0. ENV + GLOBALS
# =========================
load_dotenv()
INDEX_DIR = pathlib.Path("./index")
INDEX_DIR.mkdir(exist_ok=True)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

PDF_PATH = "1. Self-Help Author Samuel Smiles.pdf"
PDF_NAME = pathlib.Path(PDF_PATH).name

genai.configure(api_key=GOOGLE_API_KEY)

# =========================
# 1. DOC LOADING + SPLITTING
# =========================
def load_doc(path):
    return PyPDFLoader(path).load()

def split_doc(pages):
    return RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    ).split_documents(pages)

# =========================
# 2. GEMINI EMBEDDINGS (no LangChain)
# =========================
class GeminiEmbeddings:
    def __init__(self, model="models/embedding-001"):
        self.model = model

    def embed_documents(self, texts):
        vectors = []
        for t in texts:
            resp = genai.embed_content(model=self.model, input=t)
            vectors.append(resp["embedding"])
        return vectors

    def embed_query(self, text):
        resp = genai.embed_content(model=self.model, input=text)
        return resp["embedding"]

# helper
def get_embeddings():
    return GeminiEmbeddings()

# =========================
# 3. BUILD OR LOAD INDEX (QDRANT CLOUD)
# =========================
def build_or_load_index(pdf_path, rebuild=False):
    collection_name = pathlib.Path(pdf_path).stem.replace(" ", "_")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    embeddings = get_embeddings()

    # check if collection exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if not rebuild and collection_name in collections:
        return qdrant, collection_name, embeddings

    # otherwise create new collection
    pages = load_doc(pdf_path)
    chunks = split_doc(pages)

    vectors = embeddings.embed_documents([c.page_content for c in chunks])

    # recreate collection
    if collection_name in collections:
        qdrant.delete_collection(collection_name=collection_name)

    qdrant.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
    )

    # upload data
    qdrant.upload_points(
        collection_name=collection_name,
        points=[
            PointStruct(id=i, vector=vectors[i], payload={"text": chunks[i].page_content})
            for i in range(len(chunks))
        ],
    )

    return qdrant, collection_name, embeddings

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
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

if not st.session_state.vectorstore:
    qdrant, collection, embeddings = build_or_load_index(PDF_PATH, rebuild=False)
    st.session_state.vectorstore = (qdrant, collection, embeddings)
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

    qdrant, collection, embeddings = st.session_state.vectorstore
    query_vector = embeddings.embed_query(user_input)

    search_result = qdrant.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=4,
    )

    context = "\n\n".join([hit.payload["text"] for hit in search_result])
    model = genai.GenerativeModel("gemini-2.0-flash")
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
    chat = st.session_state.pdf_chats[st.session_state.selected_pdf]
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
