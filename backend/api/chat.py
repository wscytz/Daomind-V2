# -*- coding: utf-8 -*-
"""POST /api/chat — 普通对话"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict

from prompts import build_system_prompt, check_safety
from clients.base import ChatRequest
from clients.unified import UnifiedAPIClient
from api.deps import get_api_client

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatBody(BaseModel):
    message: str
    model: str = "glm-4-flash"
    persona: str = "standard"
    depth: str = "standard"
    history: Optional[List[Dict[str, str]]] = None


@router.post("/chat")
async def chat(body: ChatBody, api: UnifiedAPIClient = Depends(get_api_client)):
    # 安全检查
    safety = check_safety(body.message)
    if safety:
        return {"response": safety, "safety_warning": True}

    system_prompt = build_system_prompt(body.persona, body.depth)

    req = ChatRequest(
        message=body.message,
        model=body.model,
        history=body.history or [],
        system_prompt=system_prompt,
    )
    resp = await api.chat(req)

    if not resp.success:
        return {"response": resp.error or "服务不可用", "error": True}

    return {
        "response": resp.response,
        "thinking": resp.thinking,
        "inference_time_ms": resp.inference_time_ms,
        "model": resp.model,
        "usage": resp.usage,
    }
