# -*- coding: utf-8 -*-
"""GET /api/health"""

from fastapi import APIRouter, Request
import config

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    rag = request.app.state.rag_service
    return {
        "status": "ok",
        "rag_loaded": len(rag.loaded_providers),
        "providers": rag.loaded_providers,
        "models": config.get_all_model_choices(),
    }
