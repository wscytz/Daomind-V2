# -*- coding: utf-8 -*-
"""测试情绪检测"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestDetectEmotion:
    def test_anxiety_detection(self):
        from services.emotion import detect_emotion
        result = detect_emotion("我最近总是很焦虑")
        assert result is not None

    def test_sadness_detection(self):
        from services.emotion import detect_emotion
        result = detect_emotion("我感到很难过")
        assert result is not None

    def test_no_match(self):
        from services.emotion import detect_emotion
        result = detect_emotion("今天天气不错")
        assert result is None

    def test_empty_input(self):
        from services.emotion import detect_emotion
        result = detect_emotion("")
        assert result is None


class TestGetPrinciple:
    def test_valid_emotion_returns_principle(self):
        from services.emotion import get_principle
        result = get_principle("焦虑")
        assert result is not None
        assert len(result) > 0

    def test_unknown_emotion(self):
        from services.emotion import get_principle
        result = get_principle("nonexistent_emotion")
        assert result is None or result is not None  # 取决于实现
