# -*- coding: utf-8 -*-
"""RAG 增强咨询服务 — 安全检查 → RAG 检索 → 构建 Prompt → 调 LLM"""

import logging
from typing import Optional, Dict, List
from rag.service import RAGService
from clients.unified import UnifiedAPIClient
from clients.base import ChatRequest
from prompts import build_system_prompt, check_safety
from services.emotion import detect_emotion, get_principle

logger = logging.getLogger(__name__)


class CounselingService:
    def __init__(self, rag: RAGService, api: UnifiedAPIClient):
        self.rag = rag
        self.api = api

    async def counsel(self, message: str, classic: str = "daodejing",
                      persona: str = "standard", depth: str = "standard",
                      model: str = "glm-4-flash",
                      history: Optional[List[Dict]] = None) -> Dict:
        # 1. 安全检查
        safety = check_safety(message)
        if safety:
            return {"response": safety, "safety_warning": True}

        # 2. RAG 检索
        rag_result = self.rag.search(message, classic=classic, top_k=3)
        rag_context = self.rag.format_context(rag_result.get("results", []))

        # 3. 情绪检测（辅助信息）
        emotion = detect_emotion(message)
        principle = get_principle(emotion) if emotion else None

        # 4. 构建系统提示词
        system_prompt = build_system_prompt(persona, depth, rag_context)
        if principle and persona == "daoist":
            system_prompt += f"\n\n当前情绪倾向：{emotion}\n道家保健诀：{principle}"

        # 5. 调 LLM
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
