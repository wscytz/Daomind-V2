# -*- coding: utf-8 -*-
"""POST /api/chat — 普通对话（复用 CounselingService）"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict

from api.deps import get_counseling_service
from services.counseling import CounselingService

router = APIRouter()


class ChatBody(BaseModel):
    message: str
    model: str = "glm-4-flash"
    persona: str = "standard"
    depth: str = "standard"
    history: Optional[List[Dict[str, str]]] = None


@router.post("/chat")
async def chat(body: ChatBody, svc: CounselingService = Depends(get_counseling_service)):
    return await svc.counsel(
        message=body.message,
        persona=body.persona,
        depth=body.depth,
        model=body.model,
        history=body.history,
    )
