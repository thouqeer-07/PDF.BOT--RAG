from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import streamlit as st
from config import QDRANT_URL, QDRANT_API_KEY, GOOGLE_API_KEY, COLLECTION_NAME, PDF_PATH
from langchain_community.document_loaders import PyPDFLoader

# embeddings_utils.py
def build_or_load_index(collection_name=None, pdf_path=None):
    """
    Build or load a Qdrant index.
    - If pdf_path is provided → build new collection (user__pdfname).
    - If only collection_name → load existing collection.
    """

    print("[DEBUG] build_or_load_index called")
    if not QDRANT_URL or not QDRANT_API_KEY:
        st.error("QDRANT_URL or QDRANT_API_KEY not set!")
        return None

    try:
        embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            api_key=GOOGLE_API_KEY
        )

        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        if pdf_path:  # ✅ Create new collection
            print(f"[DEBUG] Creating new collection for PDF: {collection_name}")
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            progress_bar = st.progress(0, text="Embedding and indexing PDF...")
            total = len(docs)
            batch_size = max(1, total // 20)

            for i in range(0, total, batch_size):
                batch = docs[i:i + batch_size]
                QdrantVectorStore.from_documents(
                    batch,
                    embedding_model,
                    location=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    collection_name=collection_name
                )
                progress_bar.progress(min((i + batch_size) / total, 1.0),
                                      text=f"Embedding and indexing PDF... ({min(i + batch_size, total)}/{total})")

            progress_bar.empty()
            st.success(f"PDF indexed into collection: {collection_name}")
            return QdrantVectorStore.from_existing_collection(
                collection_name=collection_name,
                location=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                embedding=embedding_model
            )

        elif collection_name:  # ✅ Load existing collection
            existing_collections = [c.name for c in qdrant.get_collections().collections]
            if collection_name not in existing_collections:
                st.error(f"Collection {collection_name} not found!")
                return None

            print(f"[DEBUG] Loading existing collection: {collection_name}")
            return QdrantVectorStore.from_existing_collection(
                collection_name=collection_name,
                location=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                embedding=embedding_model
            )

        else:  # fallback
            
            return None

    except Exception as e:
        print(f"[DEBUG] Exception in build_or_load_index: {e}")
        st.error(f"Failed to load Qdrant index: {e}")
        return None
