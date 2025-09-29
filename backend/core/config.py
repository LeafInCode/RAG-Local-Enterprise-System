from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "RAG Local Enterprise System"
    app_version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # 存储路径
    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = project_root / "data"
    document_dir: Path = data_dir / "documents"
    vector_dir: Path = data_dir / "vector_db"

    # Chroma settings
    chroma_persist_directory: str = str(vector_dir)

    # Embedding model name (sentence-transformers)
    embedding_model_name: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.document_dir.mkdir(parents=True, exist_ok=True)
settings.vector_dir.mkdir(parents=True, exist_ok=True)
