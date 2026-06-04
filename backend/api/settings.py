# -*- coding: utf-8 -*-
"""POST /api/settings — 动态 Provider 配置"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict

import httpx
import config

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
    api_key: Optional[str] = ""
    model: str = "embedding-3"


class SettingsBody(BaseModel):
    providers: List[ProviderSettings]
    embedding: EmbeddingSettings


@router.get("/settings")
async def get_settings():
    return config.get_settings_snapshot()


class FetchModelsBody(BaseModel):
    base_url: str
    api_key: str
    auth_type: str = "bearer"


@router.post("/settings/fetch-models")
async def fetch_models(body: FetchModelsBody):
    """根据 base_url + api_key 自动拉取可用模型列表"""
    headers = {"Content-Type": "application/json"}
    if body.api_key:
        if body.auth_type in ("bearer", ""):
            headers["Authorization"] = f"Bearer {body.api_key}"
        elif body.auth_type == "api-key":
            headers["X-API-Key"] = body.api_key

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{body.base_url.rstrip('/')}/models", headers=headers)
        if resp.status_code != 200:
            return {"models": [], "error": f"API 返回 {resp.status_code}"}

        data = resp.json().get("data", [])
        models = []
        for m in data:
            mid = m.get("id", "")
            if not mid:
                continue
            models.append({
                "id": mid,
                "name": m.get("name", mid),
                "owned_by": m.get("owned_by", ""),
            })
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}


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

    # 先构建所有新对象，全部成功后再统一替换 app.state（原子性）
    from clients.unified import UnifiedAPIClient
    from rag.service import RAGService
    from services.counseling import CounselingService

    new_client = UnifiedAPIClient()
    emb_cfg = config.EMBEDDING_PROVIDER
    new_rag = RAGService(
        config.RAG_DATA_DIR,
        embedding_base_url=emb_cfg["base_url"],
        embedding_api_key=emb_cfg["api_key"],
        embedding_model=emb_cfg["model"],
        auth_type=emb_cfg.get("auth_type", "bearer"),
    )
    new_counseling = CounselingService(new_rag, new_client)

    # 全部成功后再替换
    old_client = getattr(request.app.state, "api_client", None)
    request.app.state.api_client = new_client
    request.app.state.rag_service = new_rag
    request.app.state.counseling_service = new_counseling
    if old_client and hasattr(old_client, "close"):
        try:
            await old_client.close()
        except Exception as e:
            logger.warning(f"关闭旧 API 客户端失败: {e}")

    models = new_client.available_models()
    logger.info(f"配置已更新 | 可用模型: {list(models.keys())} | RAG: {new_rag.loaded_providers}")

    # 脱敏：只返回前端需要的字段
    raw = config.get_all_model_choices()
    safe_models = {}
    for mid, cfg in raw.items():
        safe_models[mid] = {
            "provider": cfg.get("provider", ""),
            "api_model": cfg.get("api_model", mid),
            "label": cfg.get("label", mid),
            "tag": cfg.get("tag", ""),
        }

    return {
        "status": "ok",
        "models": safe_models,
        "rag_loaded": len(new_rag.loaded_providers),
        "providers": new_rag.loaded_providers,
    }
