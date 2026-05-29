# -*- coding: utf-8 -*-
"""GET /api/wisdom — 每日智慧卡 + 节气信息"""

from fastapi import APIRouter, Depends
from rag.service import RAGService
from api.deps import get_rag_service
from services.solar_term import get_current_term, get_wisdom_card

router = APIRouter()


@router.get("/wisdom")
async def wisdom(rag: RAGService = Depends(get_rag_service)):
    return get_wisdom_card(rag)


@router.get("/solar-term")
async def solar_term():
    return get_current_term()
