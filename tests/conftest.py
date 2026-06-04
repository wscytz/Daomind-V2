# -*- coding: utf-8 -*-
"""测试 fixtures"""

import os
import sys
import tempfile
import pytest

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# 设置测试用环境变量，避免加载真实 API key
os.environ.setdefault("ZHIPU_API_KEY", "test-zhipu-key")
os.environ.setdefault("DOUBAO_API_KEY", "test-doubao-key")
os.environ.setdefault("EMBEDDING_API_KEY", "test-embedding-key")
os.environ.setdefault(
    "DAOMIND_SETTINGS_FILE",
    os.path.join(tempfile.gettempdir(), "daomind-test-settings.json"),
)


@pytest.fixture(scope="session")
def app():
    """创建测试用 FastAPI app（跳过 RAG 初始化）"""
    from fastapi import FastAPI
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        # 最小化 lifespan：不初始化 RAG 和真实 API 客户端
        yield

    from main import app as _app
    # 不修改原有 lifespan，直接返回 app
    return _app


@pytest.fixture(scope="session")
def client(app):
    """FastAPI TestClient"""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def mock_env(monkeypatch):
    """确保测试环境有 mock 配置"""
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key-123")
    monkeypatch.setenv("DOUBAO_API_KEY", "test-key-456")

    # 重新导入 config 以应用环境变量
    import config
    import importlib
    importlib.reload(config)
    return config
