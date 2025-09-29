from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import upload
from backend.core.config import settings
from backend.utils.logger import logger

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(upload.router)

# 配置CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# 示例健康检查端点
@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server at http://{settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port, reload=settings.debug)
