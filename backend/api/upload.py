from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.upload import UploadResponse
from backend.services.doc_index import add_document_record
from backend.services.processing import (
    chunk_text,
    extract_text,
    save_upload_file,
)
from backend.services.vector_store import Metadata, vector_store
from backend.utils.logger import logger

router = APIRouter(prefix="/api/docs", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:  # noqa: B008
    """上传文件并进行文本提取和分块，支持多种文件格式
    流程：
        1）保存原始文件到 data/documents
        2）使用 unstructured 提取文本
        3）将文本分块并存储到向量数据库
        4）添加文档记录到 sqlite (docuements_index.db)
    """
    try:
        # 验证文件类型(基于后缀)
        allowed_types = [".pdf", ".docx", ".txt", ".pptx", ".xlsx"]
        filename = file.filename or f"uploaded_file_{uuid4().hex}"
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. "
                f"Allowed types: {', '.join(allowed_types)}",
            )

        # 读取并保存文件（持久化原始文件）
        content = await file.read()
        saved_path = save_upload_file(content, filename)

        # 使用 unstructured 提取文本
        try:
            text = extract_text(saved_path)
        except Exception as e:
            logger.error(f"Error extracting text from file {saved_path}: {e}")
            raise HTTPException(
                status_code=400, detail=f"Error extracting text from file: {e}"
            ) from e

        if not text:
            logger.warning(f"No text extracted from uploaded file {filename}")
            return UploadResponse(
                filename=filename, doc_id="", chunks_added=0, message="No text extracted from file"
            )

        # 文本分块（基于字符分块，对中英文友好）
        chunks = chunk_text(text)

        if not chunks:
            logger.warning(f"No chunks created from extracted text in file {filename}")
            return UploadResponse(
                filename=filename,
                doc_id="",
                chunks_added=0,
                message="No chunks created from extracted text",
            )

        # 生成文档ID
        doc_id = uuid4().hex

        # 准备元数据
        metadatas: list[Metadata] = [
            {"source": filename, "type": file_ext, "chunk_index": idx} for idx in range(len(chunks))
        ]

        # 添加文档到向量存储
        try:
            added = vector_store.add_documents(doc_id, chunks, metadatas)
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error adding documents to vector store: {e}"
            ) from e

        # 记录到文档索引（sqlite），便于后续管理和重建
        try:
            add_document_record(doc_id, filename, str(saved_path), added)
        except Exception:
            logger.exception(f"Failed to write document record for {doc_id}")

        return UploadResponse(
            filename=filename,
            doc_id=doc_id,
            chunks_added=added,
            message=f"Successfully uploaded and processed {filename}, added {added} chunks.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during file upload"
        ) from e
