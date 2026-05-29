# -*- coding: utf-8 -*-
"""POST /api/settings — 动态 Provider 配置"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict

import config
from clients.unified import UnifiedAPIClient

logger = logging.getLogger(__name__)
router = APIRouter()


class ModelEntry(BaseModel):
    api_model: str
    label: str = ""
    tag: str = ""


class ProviderSettings(BaseModel):
    name: str = "自定义"
    base_url: str
    api_key: Optional[str] = ""
    auth_type: str = "bearer"
    models: Dict[str, ModelEntry] = {}


class EmbeddingSettings(BaseModel):
    base_url: str
    api_key: str
    model: str = "embedding-3"


class SettingsBody(BaseModel):
    providers: List[ProviderSettings]
    embedding: EmbeddingSettings


@router.get("/settings")
async def get_settings():
    return config.get_settings_snapshot()


@router.post("/settings")
async def save_settings(body: SettingsBody, request: Request):
    providers_data = [p.model_dump() for p in body.providers]
    # 将 ModelEntry dict 转为 config 需要的格式
    for p in providers_data:
        models = {}
        for mid, minfo in p.get("models", {}).items():
            if isinstance(minfo, dict):
                models[mid] = minfo
            else:
                models[mid] = {"api_model": str(minfo), "label": mid, "tag": ""}
        p["models"] = models

    embedding_data = body.embedding.model_dump()
    config.save_settings(providers_data, embedding_data)

    # 重建 API 客户端
    new_client = UnifiedAPIClient()
    request.app.state.api_client = new_client

    # 重建 RAG 服务
    emb_cfg = config.EMBEDDING_PROVIDER
    from rag.service import RAGService
    new_rag = RAGService(
        config.RAG_DATA_DIR,
        embedding_base_url=emb_cfg["base_url"],
        embedding_api_key=emb_cfg["api_key"],
        embedding_model=emb_cfg["model"],
        auth_type=emb_cfg.get("auth_type", "bearer"),
    )
    request.app.state.rag_service = new_rag

    # 重建咨询
    from services.counseling import CounselingService
    request.app.state.counseling_service = CounselingService(new_rag, new_client)

    models = new_client.available_models()
    logger.info(f"配置已更新 | 可用模型: {list(models.keys())} | RAG: {new_rag.loaded_providers}")

    return {
        "status": "ok",
        "models": config.get_all_model_choices(),
        "rag_loaded": len(new_rag.loaded_providers),
        "providers": new_rag.loaded_providers,
    }
