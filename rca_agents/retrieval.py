"""Shared helper for building/querying a FAISS index over arbitrary text chunks."""

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rca_agents.llm import get_embeddings


def build_index(
    texts: list[str],
    metadatas: list[dict],
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> FAISS:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs: list[Document] = []
    for text, meta in zip(texts, metadatas):
        for chunk in splitter.split_text(text):
            docs.append(Document(page_content=chunk, metadata=meta))
    if not docs:
        raise ValueError("No documents to index")
    return FAISS.from_documents(docs, get_embeddings())


def query_index(index: FAISS, query: str, k: int = 5) -> list[tuple[Document, float]]:
    return index.similarity_search_with_score(query, k=k)
