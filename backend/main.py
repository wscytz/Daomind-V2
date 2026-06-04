# -*- coding: utf-8 -*-
"""Dao-Mind v2 后端入口 — 零 SDK 依赖"""

import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from rag.service import RAGService
from clients.unified import UnifiedAPIClient
from services.counseling import CounselingService
from api.chat import router as chat_router
from api.rag_counseling import router as rag_router
from api.health import router as health_router
from api.stream import router as stream_router
from api.settings import router as settings_router
from api.wisdom import router as wisdom_router
from api.about import router as about_router
from api.conversations import router as conversations_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# 文件日志轮转（5MB × 3）
_log_dir = config._get_user_dir()
_log_file = _log_dir / "daomind.log"
_handler = RotatingFileHandler(str(_log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(_handler)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # RAG
    emb_cfg = config.EMBEDDING_PROVIDER
    logger.info(f"初始化 RAG... Embedding: {emb_cfg['base_url']} model={emb_cfg['model']}")
    rag = RAGService(
        config.RAG_DATA_DIR,
        embedding_base_url=emb_cfg["base_url"],
        embedding_api_key=emb_cfg["api_key"],
        embedding_model=emb_cfg["model"],
        auth_type=emb_cfg.get("auth_type", "bearer"),
    )
    app.state.rag_service = rag

    # API 客户端（配置驱动）
    api_client = UnifiedAPIClient()
    app.state.api_client = api_client

    app.state.counseling_service = CounselingService(rag, api_client)

    models = api_client.available_models()
    logger.info(f"启动完成 | RAG providers: {rag.loaded_providers} | 可用模型: {list(models.keys())}")
    yield
    # 关闭 httpx 客户端连接
    for client in api_client._clients.values():
        await client.close()
    logger.info("关闭服务")


app = FastAPI(title="Dao-Mind v2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(chat_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(wisdom_router, prefix="/api")
app.include_router(about_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")

# 静态文件（生产模式）
frontend_dist = config.FRONTEND_DIR
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"前端: {frontend_dist}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
