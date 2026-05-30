# -*- coding: utf-8 -*-
"""API 客户端基类 + 数据结构"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, List


@dataclass
class ChatRequest:
    message: str
    model: str = "glm-4-flash"
    history: List[Dict[str, str]] = field(default_factory=list)
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None
    enable_thinking: Optional[bool] = None
    meta: Optional[Dict] = None


@dataclass
class ChatResponse:
    success: bool
    response: Optional[str] = None
    thinking: Optional[str] = None
    error: Optional[str] = None
    inference_time_ms: int = 0
    model: str = ""
    usage: Optional[Dict] = None


class BaseAPIClient(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    def build_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        messages = list(request.history)
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.message})
        return messages
