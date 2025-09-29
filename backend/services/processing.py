import uuid
from pathlib import Path

from backend.core.config import settings
from backend.utils.logger import logger


def save_upload_file(file_bytes: bytes, filename: str) -> Path:
    """保存上传文件到 data/documents 目录, 并返回保存的文件路径"""
    dst = settings.document_dir / f"{uuid.uuid4().hex}_{Path(filename).name}"
    dst.write_bytes(file_bytes)
    logger.info(f"Saved upload file to {dst}")
    return dst


def extract_text_simple(path: Path) -> str:
    """简单的文本提取器
    - 仅支持 .txt 文件
    - 其他类型文件返回空字符串并记录位置，便于后续替换为 unstructured/pdfminer/python-docx 等
    """
    if path.suffix.lower() == ".txt":
        raw = path.read_bytes()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode {path} as utf-8")
            return raw.decode("latin-1", errors="ignore")
    # TODO: 替换为更复杂的提取器
    logger.warning(f"no extractor for {path.suffix} files yet, return empty string")
    return ""


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> list[str]:
    """将长文本拆分为多个 chunk， 并返回 chunk 字符串列表"""
    if not text:
        return []

    tokens = text.split()
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk = " ".join(tokens[start:end])
        chunks.append(chunk)
        start = end - chunk_overlap if end < len(tokens) else end
    return chunks
