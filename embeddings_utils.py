from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
import streamlit as st
from config import QDRANT_URL, QDRANT_API_KEY, GOOGLE_API_KEY, COLLECTION_NAME

def build_or_load_index():
    print("[DEBUG] build_or_load_index called")
    print(f"[DEBUG] QDRANT_URL: {QDRANT_URL}")
    print(f"[DEBUG] QDRANT_API_KEY: {'set' if QDRANT_API_KEY else 'not set'}")
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("[DEBUG] QDRANT_URL or QDRANT_API_KEY not set!")
        st.error("QDRANT_URL or QDRANT_API_KEY not set!")
        return None
    try:
        embedding_model = OllamaEmbeddings(model="nomic-embed-text")
        print("[DEBUG] Ollama Embedding model created")
        vectordb = QdrantVectorStore.from_existing_collection(
            collection_name=COLLECTION_NAME,
            location=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            embedding=embedding_model
        )
        print("[DEBUG] QdrantVectorStore loaded")
        return vectordb
    except Exception as e:
        print(f"[DEBUG] Exception in build_or_load_index: {e}")
        st.error(f"Failed to load Qdrant index: {e}")
        return None
