# -*- coding: utf-8 -*-
"""统一 API 路由 — 配置驱动，所有 provider 共用 OpenAICompatClient"""

import logging
from functools import lru_cache
from typing import Dict

from config import get_model_config, get_all_model_choices
from .base import ChatRequest, ChatResponse
from .openai_compat import OpenAICompatClient

logger = logging.getLogger(__name__)


class UnifiedAPIClient:
    def __init__(self):
        # client 缓存: key = "base_url:api_key"
        self._clients: Dict[str, OpenAICompatClient] = {}

    def _get_client(self, base_url: str, api_key: str) -> OpenAICompatClient:
        cache_key = f"{base_url}:{api_key[:8]}"
        if cache_key not in self._clients:
            self._clients[cache_key] = OpenAICompatClient(api_key, base_url)
        return self._clients[cache_key]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        config = get_model_config(request.model)
        if not config:
            # 找不到模型时，尝试用第一个可用 provider
            all_choices = get_all_model_choices()
            if not all_choices:
                return ChatResponse(success=False, error="没有可用的 API 配置，请在 .env 中设置 API Key")
            fallback = list(all_choices.values())[0]
            config = fallback
            request.model = config["api_model"]
            logger.warning(f"模型 '{request.model}' 未配置，使用 fallback: {config['api_model']}")

        # 用实际 API 模型名替换前端显示名
        request.model = config["api_model"]
        client = self._get_client(config["base_url"], config["api_key"])
        return await client.chat(request)

    def available_models(self) -> Dict[str, str]:
        """返回 {前端名: provider名} 用于 health 端点"""
        return {name: cfg["provider"] for name, cfg in get_all_model_choices().items()}
