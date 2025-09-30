from pydantic import BaseModel


class QARequest(BaseModel):
    query: str
    top_k: int | None = 5
