"""PGVector store setup — embeddings + the langchain_postgres vector store."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from cv_screener.config import COLLECTION_NAME, DATABASE_URL, EMBEDDING_MODEL, require_api_key


def get_embeddings() -> OpenAIEmbeddings:
    require_api_key()
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def get_vectorstore() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=DATABASE_URL,
        use_jsonb=True,
    )
