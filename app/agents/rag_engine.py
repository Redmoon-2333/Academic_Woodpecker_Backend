"""RAG engine for document analysis using FAISS vector store."""
import os
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from app.agents.llm_client import get_embedding


class RAGEngine:
    """Manages document embedding, storage, and retrieval using FAISS."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.embeddings = get_embedding()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
        self._vector_store: Optional[InMemoryVectorStore] = None
        self._initialized = True

    @property
    def vector_store(self) -> InMemoryVectorStore:
        if self._vector_store is None:
            self._vector_store = InMemoryVectorStore(self.embeddings)
        return self._vector_store

    def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[str]:
        docs: List[Document] = []
        for i, text in enumerate(texts):
            chunks = self.text_splitter.create_documents(
                [text],
                [metadatas[i]] if metadatas and i < len(metadatas) else [{}],
            )
            docs.extend(chunks)
        if docs:
            ids = self.vector_store.add_documents(docs)
            return ids
        return []

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        return self.vector_store.similarity_search(query, k=k)

    def get_retriever(self, k: int = 4):
        return self.vector_store.as_retriever(search_kwargs={"k": k})

    def clear(self):
        try:
            self._vector_store = None
        except Exception:
            pass