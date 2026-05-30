# -*- coding: utf-8 -*-
"""SSE 流式聊天端点 — 复用 OpenAICompatClient.stream_chat()"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict

from api.deps import get_counseling_service
from services.counseling import CounselingService
from config import get_model_config, get_all_model_choices
from clients.unified import UnifiedAPIClient

router = APIRouter()


class StreamChatBody(BaseModel):
    message: str
    model: str = "glm-4-flash"
    persona: str = "standard"
    depth: str = "standard"
    history: Optional[List[Dict[str, str]]] = None


@router.post("/chat/stream")
async def chat_stream(
    body: StreamChatBody,
    svc: CounselingService = Depends(get_counseling_service),
):
    # 查找模型配置
    model_conf = get_model_config(body.model)
    if not model_conf:
        choices = get_all_model_choices()
        if choices:
            model_conf = list(choices.values())[0]
        else:
            async def err_gen():
                yield f"data: {json.dumps({'type': 'error', 'content': '没有可用模型，请在设置中添加服务商'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(err_gen(), media_type="text/event-stream")

    # 复用 CounselingService.prepare() 获取 system_prompt + 元数据
    prep = await svc.prepare(body.message, body.persona, body.depth)

    if prep["safety_warning"]:
        async def safety_gen():
            yield f"data: {json.dumps({'type': 'meta', 'safety_warning': True}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'content': prep['safety_text']}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(safety_gen(), media_type="text/event-stream")

    messages = list(body.history or [])
    if prep["system_prompt"]:
        messages.insert(0, {"role": "system", "content": prep["system_prompt"]})
    messages.append({"role": "user", "content": body.message})

    meta = json.dumps({
        "type": "meta", "sources": prep["sources"], "rag_details": prep["rag_details"],
        "principle": prep["principle"], "model": body.model
    }, ensure_ascii=False)

    # 获取 client（统一走 UnifiedAPIClient）
    api_client: UnifiedAPIClient = svc.api
    client = api_client._get_client(
        model_conf["base_url"], model_conf["api_key"], model_conf.get("auth_type", "bearer")
    )

    async def combined():
        yield f"data: {meta}\n\n"
        async for event in client.stream_chat(messages, model_conf["api_model"]):
            if event.get("type") == "error":
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(combined(), media_type="text/event-stream")
