# -*- coding: utf-8 -*-
"""OpenAI 兼容客户端 — 适配任何 OpenAI API 格式的服务（httpx 异步版）"""

import time
import logging
from typing import Optional, Dict

import httpx

from .base import BaseAPIClient, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class OpenAICompatClient(BaseAPIClient):
    """
    通用 OpenAI 兼容客户端（异步）
    支持: DeepSeek, 月之暗面, 阿里通义, 本地 Ollama/vLLM, 任何 OpenAI 格式 API
    """

    def __init__(self, api_key: str, base_url: str, timeout: int = 120, auth_type: str = "bearer"):
        super().__init__(api_key)
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auth_type = auth_type
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10))

    async def close(self):
        await self._client.aclose()

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            if self.auth_type in ("bearer", ""):
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.auth_type == "api-key":
                headers["X-API-Key"] = self.api_key
        return headers

    async def chat(self, request: ChatRequest) -> ChatResponse:
        messages = self.build_messages(request)

        payload: Dict = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        start = time.time()
        try:
            resp = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            ms = int((time.time() - start) * 1000)

            if resp.status_code != 200:
                return ChatResponse(
                    success=False,
                    error=f"API错误({resp.status_code}): {resp.text[:200]}",
                    inference_time_ms=ms,
                )

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return ChatResponse(success=False, error="响应为空", inference_time_ms=ms)

            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            thinking = msg.get("reasoning_content") or msg.get("thinking")
            usage = data.get("usage")

            return ChatResponse(
                success=True,
                response=content or "抱歉，暂时无法生成回复。",
                thinking=thinking,
                inference_time_ms=ms,
                model=request.model,
                usage=usage,
            )

        except httpx.TimeoutException:
            return ChatResponse(success=False, error="请求超时", inference_time_ms=int((time.time() - start) * 1000))
        except Exception as e:
            logger.error(f"OpenAI兼容客户端调用失败: {e}")
            return ChatResponse(success=False, error=str(e), inference_time_ms=int((time.time() - start) * 1000))

    async def stream_chat(self, messages: list, model: str, payload_extra: Optional[Dict] = None):
        """SSE 流式聊天，yield 每一行 SSE data"""
        payload: Dict = {"model": model, "messages": messages, "stream": True}
        if payload_extra:
            payload.update(payload_extra)

        async with self._client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._build_headers(),
            json=payload,
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                yield {"type": "error", "content": f"API {resp.status_code}: {body.decode()[:200]}"}
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    return
                import json
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        reasoning = delta.get("reasoning_content") or delta.get("thinking", "")
                        if reasoning:
                            yield {"type": "thinking", "content": reasoning}
                        if content:
                            yield {"type": "content", "content": content}
                    usage = data.get("usage")
                    if usage:
                        yield {"type": "usage", "content": usage}
                except Exception as e:
                    logger.warning(f"SSE JSON 解析失败: {e} | raw: {data_str[:100]}")
