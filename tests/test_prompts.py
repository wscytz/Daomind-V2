# -*- coding: utf-8 -*-
"""测试提示词构建、安全检查、人格RAG映射"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestBuildSystemPrompt:
    def test_standard_persona(self):
        from prompts import build_system_prompt
        result = build_system_prompt("standard", "standard")
        assert "道心" in result
        assert "温和" in result

    def test_daoist_persona(self):
        from prompts import build_system_prompt
        result = build_system_prompt("daoist", "standard")
        assert "道家" in result
        assert "老子" in result

    def test_baijuyi_persona(self):
        from prompts import build_system_prompt
        result = build_system_prompt("baijuyi", "standard")
        assert "白居易" in result or "乐天" in result

    def test_depth_brief(self):
        from prompts import build_system_prompt
        result = build_system_prompt("standard", "brief")
        assert "简明扼要" in result or "直击要点" in result

    def test_depth_deep(self):
        from prompts import build_system_prompt
        result = build_system_prompt("standard", "deep")
        assert "深入" in result

    def test_rag_context_included(self):
        from prompts import build_system_prompt
        result = build_system_prompt("standard", "standard", rag_context="《道德经》第一章")
        assert "道德经" in result
        assert "自然" in result

    def test_fallback_unknown_persona(self):
        from prompts import build_system_prompt
        result = build_system_prompt("nonexistent", "standard")
        assert "道心" in result


class TestPersonaRAGMap:
    def test_standard_no_rag(self):
        from prompts import PERSONA_RAG_MAP
        assert PERSONA_RAG_MAP["standard"] == []

    def test_baijuyi_has_poetry(self):
        from prompts import PERSONA_RAG_MAP
        assert "baijuyi" in PERSONA_RAG_MAP["baijuyi"]
        assert "baijuyi_outer" in PERSONA_RAG_MAP["baijuyi"]

    def test_daoist_multi_classic(self):
        from prompts import PERSONA_RAG_MAP
        classics = PERSONA_RAG_MAP["daoist"]
        assert "daodejing" in classics
        assert "zhuangzi" in classics
        assert "daoist_therapy" in classics
        assert len(classics) == 3

    def test_all_personas_have_entry(self):
        from prompts import PERSONA_PROMPTS, PERSONA_RAG_MAP
        for persona in PERSONA_PROMPTS:
            assert persona in PERSONA_RAG_MAP


class TestCheckSafety:
    def test_crisis_keyword_triggers(self):
        from prompts import check_safety
        for kw in ["自杀", "想死", "轻生", "自残"]:
            result = check_safety(f"我最近{kw}")
            assert result is not None
            assert "400-161-9995" in result

    def test_indirect_pattern_triggers(self):
        from prompts import check_safety
        result = check_safety("世界不需要我，一切都无所谓了")
        assert result is not None

    def test_normal_message_no_trigger(self):
        from prompts import check_safety
        result = check_safety("我今天心情不太好")
        assert result is None

    def test_empty_message(self):
        from prompts import check_safety
        result = check_safety("")
        assert result is None

    def test_all_keywords_covered(self):
        from prompts import SAFETY_KEYWORDS
        assert len(SAFETY_KEYWORDS) >= 10
        assert "自杀" in SAFETY_KEYWORDS
        assert "不想活" in SAFETY_KEYWORDS
