# -*- coding: utf-8 -*-
"""GET /api/health"""

from fastapi import APIRouter, Request
import config

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    rag = request.app.state.rag_service
    # 脱敏：只返回前端需要的字段，不暴露 api_key
    raw = config.get_all_model_choices()
    models = {}
    for mid, cfg in raw.items():
        models[mid] = {
            "provider": cfg.get("provider", ""),
            "api_model": cfg.get("api_model", mid),
            "label": cfg.get("label", mid),
            "tag": cfg.get("tag", ""),
        }
    return {
        "status": "ok",
        "rag_loaded": len(rag.loaded_providers),
        "providers": rag.loaded_providers,
        "models": models,
    }
