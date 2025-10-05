import sqlite3
from datetime import datetime
from typing import Any

from backend.core.config import settings
from backend.utils.logger import logger


def _get_conn() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    return conn


def init_db() -> None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            chunks_added INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_document_record(doc_id: str, filename: str, path: str, chunks_added: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        (
            "INSERT OR REPLACE INTO documents "
            "(doc_id, filename, path, chunks_added, created_at) "
            "VALUES (?, ?, ?, ?, ?)"
        ),
        (doc_id, filename, path, chunks_added, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    logger.info(f"Added document record: {filename} ({doc_id}) -> {chunks_added} chunks")


def get_document(doc_id: str) -> dict[str, Any] | None:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "doc_id": row[0],
        "filename": row[1],
        "path": row[2],
        "chunks_added": row[3],
        "created_at": row[4],
    }


def list_documents() -> list[dict[str, Any]]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "doc_id": row[0],
            "filename": row[1],
            "path": row[2],
            "chunks_added": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


# initialize database at import time
init_db()
