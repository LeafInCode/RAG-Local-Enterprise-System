from typing import Any

from fastapi import APIRouter

from backend.schemas.upload import QARequest
from backend.services.vector_store import vector_store
from backend.utils.logger import logger

router = APIRouter(prefix="/api/qa", tags=["qa"])


@router.post("/", response_model=list[dict[str, Any]])
async def qa(query_request: QARequest) -> list[dict[str, Any]]:
    """基于向量检索返回相关文档"""
    query_text = query_request.query
    top_k = query_request.top_k or 5

    if not query_text.strip():
        logger.warning("Received empty query text")
        return []

    results = vector_store.query(query_text=query_text, top_k=top_k)
    logger.info(f"Query: {query_text}, Top K: {top_k}, Results Found: {len(results)}")
    return results
