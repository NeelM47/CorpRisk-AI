#!/usr/bin/env python3
"""
ingest.py – Load, chunk, embed, and store documents for the SmartAgent RAG system.

This script processes all .txt files in the 'data' folder (and optionally .pdf if you install
additional dependencies). It uses a local embedding model (sentence-transformers/all-MiniLM-L6-v2)
and stores vectors in a persistent ChromaDB database. No cloud costs, fully local.
"""

import os
from pathlib import Path

# LangChain & vector store imports
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ========== CONFIGURATION ==========
DATA_DIR = Path("./data")                # Folder with your text files
CHROMA_DIR = Path("./chroma_db")         # Where to store the vector database
CHUNK_SIZE = 1000                        # Number of characters per chunk
CHUNK_OVERLAP = 200                       # Overlap between chunks
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Fast, free, good quality
# ====================================

def main():
    print("🚀 Starting ingestion process...")

    # 1. Load all .txt files from data directory
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory '{DATA_DIR}' not found. Please create it and place your .txt files inside.")

    # Use DirectoryLoader to grab all .txt files recursively
    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"✅ Loaded {len(documents)} text documents from {DATA_DIR}")

    if not documents:
        print("⚠️  No documents found. Exiting.")
        return

    # 2. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    # 3. Create embeddings (local, free)
    print(f"🔄 Loading embedding model '{EMBEDDING_MODEL}'...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},        # Use "cuda" if you have a GPU
        encode_kwargs={"normalize_embeddings": True}
    )

    # 4. Store in ChromaDB (persistent)
    print(f"💾 Creating vector store in '{CHROMA_DIR}'...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR)
    )
    vectorstore.persist()   # ensure it's saved to disk
    print(f"✅ Vector store created and persisted at {CHROMA_DIR}")

    # Optional: print a quick test retrieval
    print("\n🔍 Testing retrieval with a sample query: 'Barclays AML policy'")
    results = vectorstore.similarity_search("Barclays AML policy", k=2)
    for i, doc in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"Source: {doc.metadata.get('source', 'unknown')}")
        print(f"Content preview: {doc.page_content[:200]}...")

    print("\n🎉 Ingestion complete. You can now use the vector store in your RAG pipeline.")

if __name__ == "__main__":
    main()
