from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import streamlit as st
from config import QDRANT_URL, QDRANT_API_KEY, GOOGLE_API_KEY, COLLECTION_NAME
from langchain_community.document_loaders import PyPDFLoader
from io import BytesIO
from pypdf import PdfReader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# embeddings_utils.py
def build_or_load_index(collection_name=None, pdf_path=None, pdf_bytes: bytes = None, use_sidebar: bool = False):
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
            model="models/gemini-embedding-001",
            api_key=GOOGLE_API_KEY
        )

        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        if pdf_path or pdf_bytes:  # ✅ Create new collection
            print(f"[DEBUG] Creating new collection for PDF: {collection_name}")
            if pdf_bytes is not None:
                # Load PDF pages from bytes and create LangChain Documents (one per page)
                reader = PdfReader(BytesIO(pdf_bytes))
                page_docs = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    page_docs.append(Document(page_content=text, metadata={"page": i + 1, "source": collection_name}))

                # Split pages into smaller overlapping chunks for better retrieval
                splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=250)
                docs = splitter.split_documents(page_docs)
                # enrich chunk metadata
                for idx, d in enumerate(docs):
                    meta = d.metadata or {}
                    meta.update({"chunk_id": idx, "source": collection_name, "page": meta.get("page")})
                    d.metadata = meta
            else:
                loader = PyPDFLoader(pdf_path)
                docs = loader.load()
                # If loader produced large page documents, also perform splitting for uniformity
                try:
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=250)
                    docs = splitter.split_documents(docs)
                    for idx, d in enumerate(docs):
                        meta = d.metadata or {}
                        meta.update({"chunk_id": idx, "source": collection_name, "page": meta.get("page")})
                        d.metadata = meta
                except Exception:
                    # if splitting fails, continue with original docs
                    pass

            # Streamlit-friendly progress UI: separate progress bar and status text
            # If called from the sidebar, show progress there for better UX
            status = st.sidebar.empty() if use_sidebar else st.empty()
            progress_bar = st.sidebar.progress(0) if use_sidebar else st.progress(0)
            total = len(docs)
            batch_size = max(1, total // 20)

            print(f"[DEBUG] Total chunks to index: {total}")
            for i in range(0, total, batch_size):
                batch = docs[i:i + batch_size]
                # Use QdrantVectorStore to add documents in batches
                QdrantVectorStore.from_documents(
                    batch,
                    embedding_model,
                    location=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    collection_name=collection_name
                )
                done = min(i + batch_size, total)
                frac = min(done / max(total, 1), 1.0)
                progress_bar.progress(frac)
                status.text(f"Embedding and indexing PDF... ({done}/{total})")

            progress_bar.empty()
            status.empty()
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
    