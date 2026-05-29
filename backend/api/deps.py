# -*- coding: utf-8 -*-
"""FastAPI 依赖注入"""

from fastapi import Request
from rag.service import RAGService
from clients.unified import UnifiedAPIClient
from services.counseling import CounselingService


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_api_client(request: Request) -> UnifiedAPIClient:
    return request.app.state.api_client


def get_counseling_service(request: Request) -> CounselingService:
    return request.app.state.counseling_service
