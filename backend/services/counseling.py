# -*- coding: utf-8 -*-
"""RAG 增强咨询服务 — 人格自动驱动知识库检索"""

import logging
from typing import Optional, Dict, List
from rag.service import RAGService
from clients.unified import UnifiedAPIClient
from clients.base import ChatRequest
from prompts import build_system_prompt, check_safety, PERSONA_RAG_MAP
from services.emotion import detect_emotion, get_principle
from config import SOURCE_NAMES

logger = logging.getLogger(__name__)


class CounselingService:
    def __init__(self, rag: RAGService, api: UnifiedAPIClient):
        self.rag = rag
        self.api = api

    async def prepare(self, message: str, persona: str = "standard",
                      depth: str = "standard") -> Dict:
        """构建元数据（system_prompt, sources, rag_details, principle, safety_warning），
        不调用 LLM。供流式端点复用。"""
        safety = check_safety(message)
        if safety:
            return {"safety_warning": True, "safety_text": safety, "system_prompt": "",
                    "sources": [], "rag_details": [], "principle": None, "emotion": None}

        classics = PERSONA_RAG_MAP.get(persona, [])
        rag_result = {"results": [], "sources": []}
        rag_context = ""
        rag_details = []
        principle = None
        emotion = None

        if classics:
            rag_result = self.rag.search_multi(message, classics=classics, top_k=3)
            rag_context = self.rag.format_context(rag_result.get("results", []))
            emotion = detect_emotion(message)
            principle = get_principle(emotion) if emotion else None

            for r in rag_result.get("results", []):
                src = r.get("source", "")
                rag_details.append({
                    "source": src,
                    "source_name": SOURCE_NAMES.get(src, src),
                    "chapter": r.get("chapter", ""),
                    "title": r.get("title", ""),
                    "original": r.get("original", r.get("content", "")),
                    "translation": r.get("translation", r.get("modern_context", "")),
                    "similarity": round(r.get("similarity", 0), 3),
                })

        system_prompt = build_system_prompt(persona, depth, rag_context)
        if principle and persona == "daoist":
            system_prompt += f"\n\n当前情绪倾向：{emotion}\n道家保健诀：{principle}"

        return {
            "safety_warning": False,
            "system_prompt": system_prompt,
            "sources": rag_result.get("sources", []),
            "rag_details": rag_details,
            "principle": principle,
            "emotion": emotion,
        }

    async def counsel(self, message: str, persona: str = "standard",
                      depth: str = "standard", model: str = "glm-4-flash",
                      history: Optional[List[Dict]] = None) -> Dict:
        # 1. 安全检查 + RAG + 情绪 + prompt
        prep = await self.prepare(message, persona, depth)
        if prep["safety_warning"]:
            return {"response": prep["safety_text"], "safety_warning": True}

        # 2. 调 LLM
        req = ChatRequest(
            message=message,
            model=model,
            history=history or [],
            system_prompt=prep["system_prompt"],
        )
        resp = await self.api.chat(req)

        if not resp.success:
            return {"response": resp.error or "服务暂时不可用", "error": True}

        return {
            "response": resp.response,
            "thinking": resp.thinking,
            "sources": prep["sources"],
            "principle": prep["principle"],
            "inference_time_ms": resp.inference_time_ms,
            "model": resp.model,
            "usage": resp.usage,
        }
