# embeddings.py
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from tqdm import tqdm  # progress bar

# Load env vars
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# 1. Load PDF
pdf_path = "1. Self-Help Author Samuel Smiles.pdf"
loader = PyPDFLoader(pdf_path)
documents = loader.load()

# 2. Split text into chunks with overlap
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)
docs = text_splitter.split_documents(documents)

# 3. Add metadata
for i, doc in enumerate(docs):
    doc.metadata.update({
        "chunk_id": i,
        "source": pdf_path,
        "page": doc.metadata.get("page", None),
        "text_preview": doc.page_content[:200]
    })

# 4. Initialize embeddings (Ollama must be running locally with "nomic-embed-text")
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 5. Connect to Qdrant Cloud
qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

# 6. Upload chunks with progress bar
print(f"📑 Preparing {len(docs)} chunks for upload...")

# Instead of uploading all at once, do batch upload to show progress
batch_size = 100
for i in tqdm(range(0, len(docs), batch_size), desc="🔼 Uploading to Qdrant", unit="batch"):
    batch = docs[i: i + batch_size]
    QdrantVectorStore.from_documents(
        batch,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name="1. Self-Help Author Samuel Smiles.pdf",
        force_recreate=(i == 0)  # only recreate collection in first batch
    )

print("✅ Successfully uploaded all chunks to Qdrant!")
