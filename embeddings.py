"""embeddings.py

Utilities to build a Qdrant collection from PDF bytes entirely in-memory
so no local filesystem I/O is performed.

Usage: call build_index_from_pdf_bytes(pdf_bytes, collection_name)
"""
import uuid
from io import BytesIO
from typing import List
from tqdm import tqdm
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import QDRANT_URL, QDRANT_API_KEY, GOOGLE_API_KEY


def load_documents_from_bytes(pdf_bytes: bytes, collection_name: str) -> List[Document]:
    """Load a list of langchain Documents from PDF bytes.

    Each page becomes one Document with metadata.page set to the 1-based page number.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    documents: List[Document] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # keep the original source and page metadata
        documents.append(Document(page_content=text, metadata={"page": i + 1, "source": collection_name}))
    return documents


def build_index_from_pdf_bytes(pdf_bytes: bytes, collection_name: str) -> None:
    """Build / recreate a Qdrant collection from PDF bytes entirely in memory.

    - Splits text into overlapping chunks
    - Generates embeddings using Google Generative AI
    - Uploads points to Qdrant

    Params:
      pdf_bytes: raw PDF file bytes
      collection_name: target collection name in Qdrant
    """
    # 1. Load Documents from bytes
    documents = load_documents_from_bytes(pdf_bytes, collection_name)

    # 2. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=250, length_function=len)
    docs = text_splitter.split_documents(documents)

    # Add metadata to chunks
    for i, doc in enumerate(docs):
        doc.metadata.update({
            "chunk_id": i,
            "source": collection_name,
            "page": doc.metadata.get("page", None),
            "text_preview": doc.page_content[:200],
        })

    # 3. Initialize embeddings (Google Generative AI)
    embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-004", api_key=GOOGLE_API_KEY)

    # 4. Connect to Qdrant
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 5. Create/recreate collection
    qdrant.recreate_collection(collection_name=collection_name, vectors_config=VectorParams(size=768, distance=Distance.COSINE))

    # 6. Upload in batches
    batch_size = 50
    for i in tqdm(range(0, len(docs), batch_size), desc="🔼 Uploading", unit="batch"):
        batch = docs[i: i + batch_size]

        # Generate embeddings
        vectors = embeddings.embed_documents([doc.page_content for doc in batch])

        # Create points with UUIDs
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={**doc.metadata, "page_content": doc.page_content, "text": doc.page_content},
            )
            for doc, vec in zip(batch, vectors)
        ]

        # Upload to Qdrant
        qdrant.upsert(collection_name=collection_name, points=points, wait=True)

    print("✅ All chunks successfully uploaded to Qdrant with overlap!")


__all__ = ["build_index_from_pdf_bytes", "load_documents_from_bytes"]
