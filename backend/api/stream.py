# -*- coding: utf-8 -*-
"""SSE 流式聊天端点 — 人格自动驱动 RAG 检索"""

import json
import logging
import asyncio
import queue
import threading
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict

from prompts import build_system_prompt, check_safety, PERSONA_RAG_MAP
from clients.base import ChatRequest
from clients.unified import UnifiedAPIClient
from rag.service import RAGService
from services.emotion import detect_emotion, get_principle
from api.deps import get_api_client, get_rag_service
from config import get_model_config

import requests as req_lib

logger = logging.getLogger(__name__)
router = APIRouter()


class StreamChatBody(BaseModel):
    message: str
    model: str = "glm-4-flash"
    persona: str = "standard"
    depth: str = "standard"
    history: Optional[List[Dict[str, str]]] = None


def _run_stream(base_url: str, api_key: str, api_model: str, messages: list, q: queue.Queue):
    """在独立线程跑 OpenAI 兼容 SSE 流"""
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": api_model, "messages": messages, "stream": True}

        resp = req_lib.post(
            f"{base_url}/chat/completions",
            headers=headers, json=payload,
            timeout=120, stream=True,
        )
        with resp:
            if resp.status_code != 200:
                q.put(f"data: {json.dumps({'type': 'error', 'content': f'API {resp.status_code}'}, ensure_ascii=False)}\n\n")
                return
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        reasoning = delta.get("reasoning_content") or delta.get("thinking", "")
                        if reasoning:
                            q.put(f"data: {json.dumps({'type': 'thinking', 'content': reasoning}, ensure_ascii=False)}\n\n")
                        if content:
                            q.put(f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n")
                    usage = data.get("usage")
                    if usage:
                        q.put(f"data: {json.dumps({'type': 'usage', 'content': usage}, ensure_ascii=False)}\n\n")
                except json.JSONDecodeError as e:
                    logger.warning(f"SSE JSON 解析失败: {e} | raw: {data_str[:100]}")
    except Exception as e:
        q.put(f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n")
    finally:
        q.put(None)


async def _stream_from_queue(q: queue.Queue):
    loop = asyncio.get_running_loop()
    while True:
        item = await loop.run_in_executor(None, q.get)
        if item is None:
            break
        yield item


@router.post("/chat/stream")
async def chat_stream(
    body: StreamChatBody,
    api: UnifiedAPIClient = Depends(get_api_client),
    rag: RAGService = Depends(get_rag_service),
):
    # 安全检查
    safety = check_safety(body.message)
    if safety:
        async def safety_gen():
            yield f"data: {json.dumps({'type': 'content', 'content': safety}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(safety_gen(), media_type="text/event-stream")

    # 人格驱动 RAG 路由
    rag_context, sources, principle = "", [], None
    classics = PERSONA_RAG_MAP.get(body.persona, [])

    if classics:
        try:
            rag_result = rag.search_multi(body.message, classics=classics, top_k=3)
            rag_context = rag.format_context(rag_result.get("results", []))
            sources = rag_result.get("sources", [])
            # 道家人格：情绪→原则映射
            emotion = detect_emotion(body.message)
            principle = get_principle(emotion) if emotion else None
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

    system_prompt = build_system_prompt(body.persona, body.depth, rag_context)
    if principle and body.persona == "daoist":
        system_prompt += f"\n\n当前情绪倾向：{detect_emotion(body.message)}\n道家保健诀：{principle}"

    messages = list(body.history or [])
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": body.message})

    # 查找模型配置
    config = get_model_config(body.model)
    if not config:
        from config import get_all_model_choices
        choices = get_all_model_choices()
        if choices:
            config = list(choices.values())[0]
        else:
            async def err_gen():
                yield f"data: {json.dumps({'type': 'error', 'content': '没有可用模型，请在设置中添加服务商'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(err_gen(), media_type="text/event-stream")

    meta = json.dumps({
        "type": "meta", "sources": sources, "principle": principle, "model": body.model
    }, ensure_ascii=False)

    q = queue.Queue()
    t = threading.Thread(
        target=_run_stream,
        args=(config["base_url"], config["api_key"], config["api_model"], messages, q),
        daemon=True,
    )
    t.start()

    async def combined():
        yield f"data: {meta}\n\n"
        async for chunk in _stream_from_queue(q):
            yield chunk
        yield "data: [DONE]\n\n"
        t.join(timeout=2)

    return StreamingResponse(combined(), media_type="text/event-stream")
