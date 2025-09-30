from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    doc_id: str
    chunks_added: int
    message: str | None = "upload and indexed"
