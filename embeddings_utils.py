from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import streamlit as st
from config import QDRANT_URL, QDRANT_API_KEY, GOOGLE_API_KEY, COLLECTION_NAME, PDF_PATH
from langchain_community.document_loaders import PyPDFLoader

def build_or_load_index(collection_or_pdf=None):
    print("[DEBUG] build_or_load_index called")
    print(f"[DEBUG] QDRANT_URL: {QDRANT_URL}")
    print(f"[DEBUG] QDRANT_API_KEY: {'set' if QDRANT_API_KEY else 'not set'}")
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("[DEBUG] QDRANT_URL or QDRANT_API_KEY not set!")
        st.error("QDRANT_URL or QDRANT_API_KEY not set!")
        return None
    try:
        embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            api_key=GOOGLE_API_KEY
        )
        print("[DEBUG] Google Generative AI Embedding model created for queries")
        if collection_or_pdf:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            existing_collections = [c.name for c in qdrant.get_collections().collections]
            # Always use the exact filename as the collection name
            collection_name = collection_or_pdf
            if collection_name in existing_collections:
                vectordb = QdrantVectorStore.from_existing_collection(
                    collection_name=collection_name,
                    location=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    embedding=embedding_model
                )
                print(f"[DEBUG] QdrantVectorStore loaded for collection: {collection_name}")
            else:
                # Assume it's a PDF path, create new collection
                print(f"[DEBUG] Creating new collection for PDF: {collection_name}")
                loader = PyPDFLoader(collection_name)
                docs = loader.load()
                # Add progress bar for embeddings
                progress_bar = st.progress(0, text="Embedding and indexing PDF...")
                total = len(docs)
                batch_size = max(1, total // 20)  # update bar every 5% or at least every doc
                embedded_docs = []
                for i in range(0, total, batch_size):
                    batch = docs[i:i+batch_size]
                    # Actually embed and index this batch
                    vectordb = QdrantVectorStore.from_documents(
                        batch,
                        embedding_model,
                        location=QDRANT_URL,
                        api_key=QDRANT_API_KEY,
                        collection_name=collection_name
                    )
                    embedded_docs.extend(batch)
                    progress_bar.progress(min((i+batch_size)/total, 1.0), text=f"Embedding and indexing PDF... ({min(i+batch_size, total)}/{total})")
                progress_bar.empty()
                print(f"[DEBUG] QdrantVectorStore created for uploaded PDF: {collection_name}")
                # Set selected_pdf to the new PDF and rerun to show chat interface
                st.session_state.selected_pdf = collection_name
                st.rerun()
        else:
            vectordb = QdrantVectorStore.from_existing_collection(
                collection_name=COLLECTION_NAME,
                location=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                embedding=embedding_model
            )
            print("[DEBUG] QdrantVectorStore loaded for default PDF")
        return vectordb
    except Exception as e:
        print(f"[DEBUG] Exception in build_or_load_index: {e}")
        st.error(f"Failed to load Qdrant index: {e}")
        return None
