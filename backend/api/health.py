# -*- coding: utf-8 -*-
"""GET /api/health"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    rag = request.app.state.rag_service
    api = request.app.state.api_client
    return {
        "status": "ok",
        "rag_loaded": len(rag.loaded_providers),
        "providers": rag.loaded_providers,
        "models": list(api.available_models().keys()),
    }
