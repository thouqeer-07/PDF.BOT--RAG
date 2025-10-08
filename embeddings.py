# embeddings.py
import os
import uuid
from dotenv import load_dotenv
from tqdm import tqdm
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 1. Load environment variables
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 2. PDF input
"""
PDFs should be loaded from cloud (Google Drive) and not from local disk.
Refactor this script to accept PDF bytes (from Drive) and save to a temp file only for PyPDFLoader compatibility.
Remove any hardcoded local file logic.
"""
pdf_path = None  # Set by caller, should be a temp file from cloud bytes
collection_name = None  # Set by caller, should be user__pdfname

# 3. Load and split PDF
loader = PyPDFLoader(pdf_path)
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=250,  # ensures overlap
    length_function=len
)
docs = text_splitter.split_documents(documents)

# Add metadata
for i, doc in enumerate(docs):
    doc.metadata.update({
        "chunk_id": i,
        "source": pdf_path,
        "page": doc.metadata.get("page", None),
        "text_preview": doc.page_content[:200],
    })

print(f"📑 Prepared {len(docs)} chunks with overlap...")

# 4. Initialize embeddings (Google Generative AI)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    api_key=GOOGLE_API_KEY
)

# 5. Connect to Qdrant
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# 6. Create/recreate collection
qdrant.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
print(f"📂 Collection '{collection_name}' created in Qdrant.")

# 7. Upload in batches
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
            payload=doc.metadata | {"page_content": doc.page_content, "text": doc.page_content}
        )
        for doc, vec in zip(batch, vectors)
    ]

    # Upload to Qdrant
    qdrant.upsert(
        collection_name=collection_name,
        points=points,
        wait=True
    )

print("✅ All chunks successfully uploaded to Qdrant with overlap!")
