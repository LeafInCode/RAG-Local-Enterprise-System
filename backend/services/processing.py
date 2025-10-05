import re
import uuid
from pathlib import Path
from typing import BinaryIO

from unstructured.partition.auto import partition

from backend.core.config import settings
from backend.utils.logger import logger


def save_upload_file(file_bytes: bytes, filename: str) -> Path:
    """保存上传文件到 data/documents 目录, 并返回保存的文件路径"""
    dst = settings.document_dir / f"{uuid.uuid4().hex}_{Path(filename).name}"
    dst.write_bytes(file_bytes)
    logger.info(f"Saved upload file to {dst}")
    return dst


def extract_text_simple(path: Path) -> str:
    """简单的文本提取器, 仅支持 .txt 文件"""
    if path.suffix.lower() == ".txt":
        raw = path.read_bytes()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode {path} as utf-8")
            return raw.decode("latin-1", errors="ignore")
    logger.warning(f"no extractor for {path.suffix} files yet, return empty string")
    return ""


def extract_text_unstructured_from_path(path: Path) -> str:
    """使用 unstructured.partition 从文件路径提取文本
    partition 函数会根据文件类型自动选择合适的提取器
    """
    try:
        elements = partition(filename=str(path))
        text = "\n".join(
            [
                el.get("text", "") if isinstance(el, dict) else getattr(el, "text", "") or ""
                for el in elements
            ]
        )
        # filter multiple empty lines
        text = "\n".join([line for line in (t.strip() for t in text.splitlines()) if line])
        return text
    except Exception as e:
        logger.error(f"unstructured failed to parse {path}: {e}")
        raise


def extract_text_unstructured_from_bytes(file: BinaryIO) -> str:
    """
    如果只有 bytesIO（例如不想先保存文件），unstructured 也可通过 file=... 使用。
    但这里我们主要使用基于路径的方式（更稳定），此函数为备用实现。
    """
    try:
        elements = partition(file=file)
        text = "\n".join(
            [
                el.get("text", "") if isinstance(el, dict) else getattr(el, "text", "") or ""
                for el in elements
            ]
        )
        text = "\n".join([line for line in (t.strip() for t in text.splitlines()) if line])
        return text
    except Exception as e:
        logger.exception(f"unstructured failed to parse file-like object: {e}")
        raise


# processing.py
def extract_text(path: Path) -> str:
    """统一的文本提取入口。优先采用 untructured(文件路径方式)"""
    try:
        text = extract_text_unstructured_from_path(path)
        if text:
            return text.strip()
    except Exception as e:
        logger.warning(f"unstructured failed to parse {path}: {e}, fallback to simple extractor")

    # fallback to simple extractor
    return extract_text_simple(path)


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> list[str]:
    """将长文本拆分为多个 chunk， 并返回 chunk 字符串列表"""
    if not text:
        return []

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap if end < text_len else end
    return chunks
