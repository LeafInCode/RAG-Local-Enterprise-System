from uuid import uuid4

from fastapi import APIRouter, File, UploadFile

from backend.schemas.upload import UploadResponse
from backend.services.processing import chunk_text, extract_text_simple, save_upload_file
from backend.services.vector_store import Metadata, vector_store
from backend.utils.logger import logger

router = APIRouter(prefix="/api/docs", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:  # noqa: B008
    context = await file.read()
    filename = file.filename or f"uploaded_file_{uuid4().hex}"
    path = save_upload_file(context, filename)
    text = extract_text_simple(path)
    chunks = chunk_text(text)
    doc_id = uuid4().hex
    if chunks:
        # 确保 metadatas 类型符合要求，使用Metadata类型注解
        metadatas: list[Metadata] = (
            [{"source": filename} for _ in chunks] if filename else [{} for _ in chunks]
        )
        added = vector_store.add_documents(doc_id, chunks, metadatas)
    else:
        added = 0
        logger.warning(f"No chunks extracted from uploaded file {filename}")
    return UploadResponse(
        filename=filename,
        doc_id=doc_id,
        chunks_added=added,
        message="upload and indexed" if added > 0 else "upload but no chunks indexed",
    )
