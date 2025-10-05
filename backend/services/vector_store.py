from collections.abc import Mapping
from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from backend.core.config import settings
from backend.utils.logger import logger

MetadataValue = str | int | float | bool | None
Metadata = Mapping[str, MetadataValue]


class VectorStore:
    def __init__(
        self, persist_directory: str | None = None, embedding_model_name: str | None = None
    ):
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.client = chromadb.Client(ChromaSettings(persist_directory=self.persist_directory))
        self.collection = self.client.get_or_create_collection(name="docs")
        self.embedding_model_name = embedding_model_name or settings.embedding_model_name
        self._embedder = SentenceTransformer(self.embedding_model_name)
        logger.info(
            f"VectorStore initialized with persist_directory={self.persist_directory} and "
            f"embedding_model_name={self.embedding_model_name}"
        )

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return self._embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    def add_documents(
        self, doc_id: str, chunks: list[str], metadatas: list[Metadata] | None = None
    ) -> int:
        """添加文档的 chunks 到向量数据库"""
        if not chunks:
            logger.warning(f"No chunks to add for doc_id={doc_id}")
            return 0

        # 过滤空白 chunks
        clean_chunks, clean_metas = [], []
        for chunk, meta in zip(chunks, metadatas or [{} for _ in chunks], strict=False):
            if chunk and chunk.strip():
                clean_chunks.append(chunk.strip())
                clean_metas.append(meta)
            else:
                logger.debug(f"Skipping empty chunk with metadata: {meta}")

        if not clean_chunks:
            logger.warning(f"All chunks empty for doc_id={doc_id}")
            return 0

        ids = [f"{doc_id}_{i}" for i in range(len(clean_chunks))]

        # 直接使用列表推导式创建符合要求的元数据列表
        validated_metadatas: list[Metadata] = [
            {k: v for k, v in (meta or {}).items() if isinstance(v, (str, int, float, bool))}
            for meta in clean_metas
        ]
        embeddings = self.embed_texts(clean_chunks)
        self.collection.add(
            ids=ids,
            documents=clean_chunks,
            metadatas=validated_metadatas,  # type: ignore[arg-type]
            embeddings=embeddings,
        )

        if hasattr(self.client, "persist"):
            self.client.persist()
        logger.info(f"Added {len(clean_chunks)} chunks for doc_id={doc_id} to vector store")
        return len(clean_chunks)

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """基于查询文本，从向量数据库中检索 top_k 相关的 chunks"""
        if not query_text:
            logger.warning("Empty query_text provided for vector store query")
            return []

        query_embedding = self.embed_texts([query_text])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        # 确保结果不为None且有对应字段
        if results.get("documents") and results.get("metadatas") and results.get("distances"):
            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []

            for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
                retrieved.append({"document": doc, "metadata": meta, "distance": dist})

        logger.info(f"Retrieved {len(retrieved)} results for query: {query_text}")
        return retrieved


# 单例模式，方便全局使用
vector_store = VectorStore()
