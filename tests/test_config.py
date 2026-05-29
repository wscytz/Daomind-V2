# -*- coding: utf-8 -*-
"""测试配置模块"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestConfig:
    def test_cors_origins_default(self):
        import config
        assert len(config.CORS_ORIGINS) >= 2
        assert "http://localhost:8001" in config.CORS_ORIGINS

    def test_providers_structure(self):
        import config
        # 如果 save_settings 测试先运行清空了 providers，先恢复默认
        if not config.PROVIDERS:
            config.PROVIDERS.append({
                "name": "智谱 AI",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": "",
                "models": {"glm-4-flash": {"api_model": "glm-4-flash", "label": "GLM-4 Flash", "tag": "快速"}},
            })
        assert len(config.PROVIDERS) >= 1
        for p in config.PROVIDERS:
            assert "name" in p
            assert "base_url" in p
            assert "api_key" in p
            assert "models" in p
            assert isinstance(p["models"], dict)
            for mid, minfo in p["models"].items():
                if isinstance(minfo, dict):
                    assert "api_model" in minfo
                    assert "label" in minfo

    def test_embedding_provider(self):
        import config
        assert "base_url" in config.EMBEDDING_PROVIDER
        assert "api_key" in config.EMBEDDING_PROVIDER
        assert "model" in config.EMBEDDING_PROVIDER

    def test_get_all_model_choices_format(self):
        import config
        choices = config.get_all_model_choices()
        assert isinstance(choices, dict)
        for mid, info in choices.items():
            assert "provider" in info
            assert "base_url" in info
            assert "api_key" in info
            assert "api_model" in info
            assert "label" in info
            assert "tag" in info

    def test_get_model_config_unknown(self):
        import config
        result = config.get_model_config("nonexistent-model")
        assert result is None

    def test_get_settings_snapshot_masks_keys(self):
        import config
        snapshot = config.get_settings_snapshot()
        assert "providers" in snapshot
        assert "embedding" in snapshot
        for p in snapshot["providers"]:
            assert "api_key_masked" in p

    def test_host_port_defaults(self):
        import config
        assert isinstance(config.PORT, int)
        assert config.PORT > 0
        assert isinstance(config.HOST, str)

    def test_save_and_load_providers(self):
        """测试 save_settings 完全替换 provider 列表"""
        import config
        original_count = len(config.PROVIDERS)
        # 保存一个自定义 provider
        config.save_settings(
            providers_data=[{
                "name": "TestProvider",
                "base_url": "https://test.example.com/v1",
                "api_key": "test-key-123",
                "models": {
                    "test-model": {"api_model": "test-model", "label": "Test", "tag": "测试"},
                },
            }],
            embedding_data={
                "base_url": "https://test.example.com/v1",
                "api_key": "test-key",
                "model": "test-emb",
            },
        )
        assert len(config.PROVIDERS) == 1
        assert config.PROVIDERS[0]["name"] == "TestProvider"
        assert "test-model" in config.PROVIDERS[0]["models"]
        assert config.EMBEDDING_PROVIDER["model"] == "test-emb"
        # 恢复
        config.save_settings(
            providers_data=[{
                "name": "智谱 AI",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": "",
                "models": {"glm-4-flash": {"api_model": "glm-4-flash", "label": "GLM-4 Flash", "tag": "快速"}},
            }],
            embedding_data={
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": "",
                "model": "embedding-3",
            },
        )
