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
        assert len(config.PROVIDERS) >= 1
        for p in config.PROVIDERS:
            assert "name" in p
            assert "base_url" in p
            assert "api_key" in p
            assert "models" in p

    def test_embedding_provider(self):
        import config
        assert "base_url" in config.EMBEDDING_PROVIDER
        assert "api_key" in config.EMBEDDING_PROVIDER
        assert "model" in config.EMBEDDING_PROVIDER

    def test_get_all_model_choices_without_keys(self):
        import config
        # 测试环境没有真实 key，应返回空或 0 模型
        choices = config.get_all_model_choices()
        # 测试 key 不为空字符串，应返回一些模型
        assert isinstance(choices, dict)

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
            # 脱敏后的 key 不应该等于原始 key（如果 key 长度 > 8）
            if len(p["api_key"]) > 8:
                assert "****" in p["api_key_masked"]

    def test_host_port_defaults(self):
        import config
        assert isinstance(config.PORT, int)
        assert config.PORT > 0
        assert isinstance(config.HOST, str)
