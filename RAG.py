# =========================
# 1. DOCUMENT LOADING
# =========================
import os
import pathlib
import pickle
import numpy as np
from dotenv import load_dotenv
import requests
from langchain_community.document_loaders import PyPDFLoader
load_dotenv()
INDEX_DIR = pathlib.Path("./index")
INDEX_DIR.mkdir(exist_ok=True)
def load_doc(pdf_path):
    loader = PyPDFLoader(pdf_path)  
    return loader.load()
# =========================
# 2. DOCUMENT SPLITTING
# =========================
from langchain.text_splitter import RecursiveCharacterTextSplitter
def split_doc(pages):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    return splitter.split_documents(pages)
# =========================
# 3. VECTORSTORES & EMBEDDINGS
# =========================
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings

class OllamaEmbeddings(Embeddings):
    def __init__(self, model="nomic-embed-text", url="http://localhost:11434/api/embed"):
        self.model = model
        self.url = url

    def _get_embedding(self, text: str):    
        payload = {"model": self.model, "input": text}
        response = requests.post(self.url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["embeddings"][0] if "embeddings" in data else None
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

    def embed_documents(self, texts):
        payload = {"model": self.model, "input": texts}
        response = requests.post(self.url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["embeddings"] if "embeddings" in data else None
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

    def embed_query(self, text):
        return self._get_embedding(text)

def build_or_load_index(pdf_path, rebuild=False):
    index_fp = INDEX_DIR / ("faiss_" + pathlib.Path(pdf_path).stem.replace(" ", "_"))
    store_fp = index_fp.with_suffix(".pkl")
    emb_cache_fp = INDEX_DIR / (pathlib.Path(pdf_path).stem.replace(" ", "_") + "_embeddings.npy")
    embeddings = OllamaEmbeddings()

    if not rebuild and index_fp.exists() and store_fp.exists():
        vectorstore = FAISS.load_local(str(index_fp), embeddings, allow_dangerous_deserialization=True)
        test_vec = embeddings.embed_query("test")
        if len(test_vec) == vectorstore.index.d:
            return vectorstore

    # Load and split PDF
    pages = load_doc(pdf_path)
    splits = split_doc(pages)

    # Compute or load embeddings
    if emb_cache_fp.exists():
        embeddings_list = np.load(emb_cache_fp, allow_pickle=True)
    else:
        embeddings_list = embeddings.embed_documents([d.page_content for d in splits])
        np.save(emb_cache_fp, embeddings_list)

    # Store in FAISS
    vectorstore = FAISS.from_documents(splits, embeddings)
    vectorstore.save_local(str(index_fp))
    with open(store_fp, "wb") as f:
        pickle.dump(vectorstore.index_to_docstore_id, f)
    return vectorstore

# =========================
# 4. RETRIEVAL
# =========================
from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = """You are a precise, concise assistant. 
Answer strictly based on the retrieved context.
If the answer is not in the context, say you don't know based on the provided PDF.
"""

QA_TEMPLATE = """{system}
# Context:
{context}
# Question:
{question}
# Instructions:
- Answer in 2-5 sentences unless the user asks for more detail.
"""

def get_retriever(vectorstore):
    return vectorstore.as_retriever(search_kwargs={"k": 4})

def get_prompt():
    return PromptTemplate(
        template=QA_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )

# =========================
# 5. STREAMLIT UI
# =========================
import streamlit as st
import google.generativeai as genai
st.set_page_config(page_title="RAG Chatbot", layout="wide")
st.markdown("<h1 style='text-align:center;color:Gold;'>📚 PDF Chatbot Assistant</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:Brown;'>RAG PIPELINE</h4>", unsafe_allow_html=True)

# Initialize session state
if "pdf_chats" not in st.session_state:
    st.session_state.pdf_chats = {}
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "vectorstores" not in st.session_state:
    st.session_state.vectorstores = {}
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# Sidebar PDF upload and history
uploaded_file = st.sidebar.file_uploader("Upload a PDF", type=["pdf"])
if uploaded_file:
    pdf_name = uploaded_file.name
    pdf_path = INDEX_DIR / pdf_name
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    if pdf_name not in st.session_state.vectorstores:
        vectordb = build_or_load_index(pdf_path, rebuild=False)
        st.session_state.vectorstores[pdf_name] = vectordb
        st.session_state.pdf_chats[pdf_name] = []
    st.session_state.selected_pdf = pdf_name
    st.sidebar.success(f"✅ {pdf_name} loaded!")

st.sidebar.markdown("### PDF History")
for pdf_name in st.session_state.pdf_chats.keys():
    if st.sidebar.button(pdf_name):
        st.session_state.selected_pdf = pdf_name

# Chat logic
def send_message():
    user_input = st.session_state.input_text.strip()
    if not user_input:
        return

    # Friendly replies              
    greetings = {"hi","hello","hey","hiya","hii"}
    farewells = {"bye","goodbye","exit","quit"}
    thanks = {"thanks","thank you","thx"}

    if user_input.lower() in greetings:
        bot_reply = "Hello! 👋 How can I help you today?"
    elif user_input.lower() in farewells:
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif user_input.lower() in thanks:
        bot_reply = "You're welcome! 😊"
    else:
        vectordb = st.session_state.vectorstores[st.session_state.selected_pdf]
        retriever = get_retriever(vectordb)

        # Configure Gemini API
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Build prompt
        prompt = get_prompt()
        with st.spinner("🤖 Thinking..."):
            docs = retriever.get_relevant_documents(user_input)
            context = "\n\n".join([d.page_content for d in docs])
            final_prompt = prompt.format(context=context, question=user_input)

            # Call Gemini API
            response = model.generate_content(final_prompt)
            bot_reply = response.text.strip()

    # Append messages
    st.session_state.pdf_chats[st.session_state.selected_pdf].append(
        {"role": "user", "content": user_input}
    )
    st.session_state.pdf_chats[st.session_state.selected_pdf].append(
        {"role": "assistant", "content": bot_reply}
    )
    st.session_state.input_text = ""


# =========================
# CHAT INTERFACE
# =========================
if st.session_state.selected_pdf:
    pdf_name = st.session_state.selected_pdf
    st.markdown(f"<h3 style='color:purple;'>Chat Interface - {pdf_name}</h3>", unsafe_allow_html=True)

    chats = st.session_state.pdf_chats[pdf_name]

    # Display chat bubbles
    for msg in chats:
        if msg["role"]=="user":
            st.markdown(f"""
            <div style="display:flex; justify-content:flex-end; margin:5px 0;">
                <div style="background-color:lightblue; color:#000; padding:12px; border-radius:12px; max-width:70%; font-size:16px; line-height:1.5; word-wrap:break-word;">
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display:flex; justify-content:flex-start; margin:5px 0;">
                <div style="background-color:#F1F0F0; color:#000; padding:12px; border-radius:12px; max-width:70%; font-size:16px; line-height:1.5; word-wrap:break-word;">
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.text_input("Type your question here...", key="input_text", on_change=send_message)
else:
    st.write("Please upload or select a PDF to start chatting.")


