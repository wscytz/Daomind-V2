# -*- coding: utf-8 -*-
"""统一 API 路由 — 配置驱动，所有 provider 共用 OpenAICompatClient"""

import hashlib
import logging
from typing import Dict

from config import get_model_config, get_all_model_choices
from .base import ChatRequest, ChatResponse
from .openai_compat import OpenAICompatClient

logger = logging.getLogger(__name__)


def _key_hash(api_key: str) -> str:
    """用完整 key 的 SHA256 前 16 位做缓存键，防止前 8 位冲突"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


class UnifiedAPIClient:
    def __init__(self):
        self._clients: Dict[str, OpenAICompatClient] = {}

    def _get_client(self, base_url: str, api_key: str, auth_type: str = "bearer") -> OpenAICompatClient:
        cache_key = f"{base_url}:{_key_hash(api_key)}:{auth_type}"
        if cache_key not in self._clients:
            self._clients[cache_key] = OpenAICompatClient(api_key, base_url, auth_type=auth_type)
        return self._clients[cache_key]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        original_model = request.model  # 先保存原始模型名再赋值
        config = get_model_config(request.model)
        if not config:
            all_choices = get_all_model_choices()
            if not all_choices:
                return ChatResponse(success=False, error="没有可用的 API 配置，请在设置中添加服务商")
            fallback = list(all_choices.values())[0]
            config = fallback
            logger.warning(f"模型 '{original_model}' 未配置，使用 fallback: {config['api_model']}")

        request.model = config["api_model"]
        client = self._get_client(config["base_url"], config["api_key"], config.get("auth_type", "bearer"))
        return await client.chat(request)

    def available_models(self) -> Dict[str, str]:
        """返回 {model_id: provider_name} 用于 health 端点"""
        return {name: cfg["provider"] for name, cfg in get_all_model_choices().items()}
