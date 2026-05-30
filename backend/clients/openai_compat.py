# -*- coding: utf-8 -*-
"""OpenAI 兼容客户端 — 适配任何 OpenAI API 格式的服务"""

import time
import json
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List
import requests as req

from .base import BaseAPIClient, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class OpenAICompatClient(BaseAPIClient):
    """
    通用 OpenAI 兼容客户端
    支持: DeepSeek, 月之暗面, 阿里通义, 本地 Ollama/vLLM, 任何 OpenAI 格式 API
    """
    # 不预设模型列表，由用户自定义
    SUPPORTED_MODELS = {}

    def __init__(self, api_key: str, base_url: str, timeout: int = 120, auth_type: str = "bearer"):
        super().__init__(api_key)
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auth_type = auth_type
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="openai_compat_")

    def close(self):
        self._executor.shutdown(wait=False)

    def __del__(self):
        self.close()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        messages = self.build_messages(request)

        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            if self.auth_type == "bearer" or not self.auth_type:
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif self.auth_type == "api-key":
                headers["X-API-Key"] = self.api_key
            # auth_type == "none" 时不加任何认证头

        start = time.time()
        try:
            loop = asyncio.get_running_loop()
            resp = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    lambda: req.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=self.timeout,
                    )
                ),
                timeout=self.timeout + 5,
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

        except asyncio.TimeoutError:
            return ChatResponse(success=False, error="请求超时", inference_time_ms=int((time.time() - start) * 1000))
        except Exception as e:
            logger.error(f"OpenAI兼容客户端调用失败: {e}")
            return ChatResponse(success=False, error=str(e), inference_time_ms=int((time.time() - start) * 1000))
