# -*- coding: utf-8 -*-
"""RAG 增强咨询服务 — 人格自动驱动知识库检索"""

import logging
from typing import Optional, Dict, List
from rag.service import RAGService
from clients.unified import UnifiedAPIClient
from clients.base import ChatRequest
from prompts import build_system_prompt, check_safety, PERSONA_RAG_MAP
from services.emotion import detect_emotion, get_principle

logger = logging.getLogger(__name__)


class CounselingService:
    def __init__(self, rag: RAGService, api: UnifiedAPIClient):
        self.rag = rag
        self.api = api

    async def counsel(self, message: str, persona: str = "standard",
                      depth: str = "standard", model: str = "glm-4-flash",
                      history: Optional[List[Dict]] = None) -> Dict:
        # 1. 安全检查
        safety = check_safety(message)
        if safety:
            return {"response": safety, "safety_warning": True}

        # 2. 人格驱动 RAG 检索
        classics = PERSONA_RAG_MAP.get(persona, [])
        rag_result = {"results": [], "sources": []}
        rag_context = ""
        principle = None

        if classics:
            rag_result = self.rag.search_multi(message, classics=classics, top_k=3)
            rag_context = self.rag.format_context(rag_result.get("results", []))

            # 道家人格：情绪→原则映射
            emotion = detect_emotion(message)
            principle = get_principle(emotion) if emotion else None

        # 3. 构建系统提示词
        system_prompt = build_system_prompt(persona, depth, rag_context)
        if principle and persona == "daoist":
            system_prompt += f"\n\n当前情绪倾向：{emotion}\n道家保健诀：{principle}"

        # 4. 调 LLM
        req = ChatRequest(
            message=message,
            model=model,
            history=history or [],
            system_prompt=system_prompt,
        )
        resp = await self.api.chat(req)

        if not resp.success:
            return {"response": resp.error or "服务暂时不可用", "error": True}

        return {
            "response": resp.response,
            "thinking": resp.thinking,
            "sources": rag_result.get("sources", []),
            "principle": principle,
            "inference_time_ms": resp.inference_time_ms,
            "model": resp.model,
            "usage": resp.usage,
        }
