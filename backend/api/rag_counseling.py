# -*- coding: utf-8 -*-
"""POST /api/rag/counseling — RAG 增强咨询（人格驱动知识库）"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict

from api.deps import get_counseling_service
from services.counseling import CounselingService

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGBody(BaseModel):
    message: str
    persona: str = "daoist"
    depth: str = "standard"
    model: str = "glm-4-flash"
    history: Optional[List[Dict[str, str]]] = None


@router.post("/rag/counseling")
async def rag_counseling(body: RAGBody, svc: CounselingService = Depends(get_counseling_service)):
    return await svc.counsel(
        message=body.message,
        persona=body.persona,
        depth=body.depth,
        model=body.model,
        history=body.history,
    )
