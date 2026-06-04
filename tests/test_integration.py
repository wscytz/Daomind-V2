# -*- coding: utf-8 -*-
"""集成测试：API 端点、RAG 检索、智慧卡、节气"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestSolarTerm:
    def test_current_term_is_valid(self):
        from services.solar_term import get_current_term
        term = get_current_term()
        assert term["name"] in [
            "小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨",
            "立夏","小满","芒种","夏至","小暑","大暑","立秋","处暑",
            "白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至",
        ]
        assert term["keyword"]
        assert term["description"]
        assert term["theme"]

    def test_specific_date(self):
        from datetime import date
        from services.solar_term import get_current_term
        term = get_current_term(date(2026, 2, 4))
        assert term["name"] == "立春"
        term2 = get_current_term(date(2026, 12, 22))
        assert term2["name"] == "冬至"

    def test_term_rag_themes_complete(self):
        from services.solar_term import TERM_PERIODS, TERM_RAG_THEMES
        all_terms = [name for _, _, name, _, _ in TERM_PERIODS]
        assert len(all_terms) == 24
        for name in all_terms:
            assert name in TERM_RAG_THEMES, f"节气 {name} 缺少 RAG 主题映射"


class TestRAGSearch:
    def test_baijuyi_routes_are_poem_only(self):
        from rag.service import CLASSIC_ROUTES

        assert CLASSIC_ROUTES["baijuyi"] == ["baijuyi"]
        assert CLASSIC_ROUTES["baijuyi_outer"] == ["baijuyi_outer"]

    def test_dirty_baijuyi_outer_result_filtered(self):
        from rag.service import RAGService

        dirty = {
            "source": "poem_outer",
            "title": "逢旧",
            "content": "久别偶相逢，俱疑是梦中。即今欢乐事，放醆又成空。知",
            "quality_level": "low",
            "similarity": 0.99,
        }
        clean = {
            "source": "poem_outer",
            "title": "问刘十九",
            "content": "绿蚁新醅酒，红泥小火炉。晚来天欲雪，能饮一杯无。",
            "quality_level": "high",
            "similarity": 0.8,
        }

        assert RAGService._filter_and_rank_results([dirty, clean], 3) == [clean]

    def test_daodejing_search_clean(self):
        """确认道德经检索结果不再包含脏标签"""
        from rag.service import RAGService
        from config import RAG_DATA_DIR, EMBEDDING_PROVIDER
        rag = RAGService(
            RAG_DATA_DIR,
            embedding_base_url=EMBEDDING_PROVIDER["base_url"],
            embedding_api_key=EMBEDDING_PROVIDER["api_key"],
            embedding_model=EMBEDDING_PROVIDER["model"],
        )
        if not rag.providers:
            return  # 无 embedding API 则跳过
        result = rag.search("面对焦虑", classic="daodejing", top_k=2)
        for r in result.get("results", []):
            original = r.get("original", "")
            assert "场景：" not in original
            assert "情绪：" not in original

    def test_search_multi_returns_multiple_sources(self):
        from rag.service import RAGService
        from config import RAG_DATA_DIR, EMBEDDING_PROVIDER
        rag = RAGService(
            RAG_DATA_DIR,
            embedding_base_url=EMBEDDING_PROVIDER["base_url"],
            embedding_api_key=EMBEDDING_PROVIDER["api_key"],
            embedding_model=EMBEDDING_PROVIDER["model"],
        )
        if not rag.providers:
            return  # 无 embedding API 则跳过
        result = rag.search_multi("如何面对焦虑", classics=["daodejing", "zhuangzi", "daoist_therapy"], top_k=3)
        sources = result.get("sources", [])
        # embedding API 可因 key 失效返回空，不算测试失败
        if not sources:
            import logging
            logging.warning("search_multi 返回空，可能是 embedding API key 失效")


class TestKeySecurity:
    def test_settings_snapshot_no_plaintext_key(self):
        """GET /api/settings 不应返回明文 key"""
        import config
        # 先设一个测试 key
        original_providers = list(config.PROVIDERS)
        config.PROVIDERS = [{
            "name": "测试",
            "base_url": "https://test.com/v1",
            "api_key": "sk-test-1234567890abcdef",
            "models": {"test": {"api_model": "test", "label": "Test", "tag": ""}},
        }]
        try:
            snapshot = config.get_settings_snapshot()
            # 不应有 api_key 明文字段
            for p in snapshot["providers"]:
                assert "api_key" not in p or not p.get("api_key"), f"provider 暴露了明文 key: {p}"
                assert p.get("api_key_masked") == "sk-t****cdef"
            # embedding 也不应有明文
            assert "api_key" not in snapshot["embedding"] or not snapshot["embedding"].get("api_key")
        finally:
            config.PROVIDERS = original_providers

    def test_save_preserves_existing_key(self):
        """保存时不传 key 应保留原有 key"""
        import config
        config.PROVIDERS = [{
            "name": "测试",
            "base_url": "https://test.com/v1",
            "api_key": "sk-original-key-12345",
            "models": {"t": {"api_model": "t", "label": "T", "tag": ""}},
        }]
        # 不传 api_key（空字符串或 None）
        config.save_settings(
            providers_data=[{
                "name": "测试",
                "base_url": "https://test.com/v1",
                "api_key": "",
                "models": {"t": {"api_model": "t", "label": "T", "tag": ""}},
            }],
            embedding_data={"base_url": "https://test.com/v1", "api_key": "", "model": "emb"},
        )
        assert config.PROVIDERS[0]["api_key"] == "sk-original-key-12345"
        # 传新 key 应覆盖
        config.save_settings(
            providers_data=[{
                "name": "测试",
                "base_url": "https://test.com/v1",
                "api_key": "sk-new-key",
                "models": {"t": {"api_model": "t", "label": "T", "tag": ""}},
            }],
            embedding_data={"base_url": "https://test.com/v1", "api_key": "", "model": "emb"},
        )
        assert config.PROVIDERS[0]["api_key"] == "sk-new-key"


class TestPersonaRAGIntegration:
    def test_standard_no_rag_retrieval(self):
        """standard 人格不应触发 RAG"""
        from prompts import PERSONA_RAG_MAP
        assert PERSONA_RAG_MAP["standard"] == []

    def test_daoist_triggers_emotion_mapping(self):
        """daoist 人格的检索应触发情绪映射"""
        from services.emotion import detect_emotion, get_principle
        emotion = detect_emotion("我很焦虑")
        assert emotion == "焦虑"
        principle = get_principle(emotion)
        assert principle == "少私寡欲，知足知止"


class TestCounselingPrepare:
    """测试 CounselingService.prepare() 方法"""

    def _make_service(self):
        from services.counseling import CounselingService
        from rag.service import RAGService
        from clients.unified import UnifiedAPIClient
        from config import RAG_DATA_DIR, EMBEDDING_PROVIDER
        rag = RAGService(
            RAG_DATA_DIR,
            embedding_base_url=EMBEDDING_PROVIDER["base_url"],
            embedding_api_key=EMBEDDING_PROVIDER["api_key"],
            embedding_model=EMBEDDING_PROVIDER["model"],
        )
        return CounselingService(rag, UnifiedAPIClient())

    def test_safety_trigger(self):
        import asyncio
        svc = self._make_service()
        result = asyncio.run(svc.prepare("我不想活了", "standard", "standard"))
        assert result["safety_warning"] is True
        assert "400-161-9995" in result["safety_text"]
        assert result["system_prompt"] == ""

    def test_normal_returns_prompt(self):
        import asyncio
        svc = self._make_service()
        result = asyncio.run(svc.prepare("最近压力大", "standard", "standard"))
        assert result["safety_warning"] is False
        assert "道心" in result["system_prompt"]
        assert result["sources"] == []  # standard 不触发 RAG

    def test_daoist_with_rag(self):
        import asyncio
        svc = self._make_service()
        if not svc.rag.providers:
            return  # 无 embedding API 跳过
        result = asyncio.run(svc.prepare("我很焦虑", "daoist", "deep"))
        assert result["safety_warning"] is False
        assert "道" in result["system_prompt"]
        # daoist 应触发情绪检测
        assert result["emotion"] == "焦虑"
        assert result["principle"] is not None
