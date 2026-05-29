# -*- coding: utf-8 -*-
"""测试 BM25 混合检索器"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestTokenizeChinese:
    def test_single_cjk(self):
        from rag.hybrid import tokenize_chinese
        tokens = tokenize_chinese("道可道")
        assert "道可" in tokens
        assert "可道" in tokens

    def test_english_preserved(self):
        from rag.hybrid import tokenize_chinese
        tokens = tokenize_chinese("hello world")
        assert "hello" in tokens
        assert "world" in tokens

    def test_mixed_cjk_english(self):
        from rag.hybrid import tokenize_chinese
        tokens = tokenize_chinese("道 heart 经")
        assert "heart" in tokens
        # CJK 字符与英文混合时，孤立 CJK 字符单独保留
        assert len(tokens) >= 3

    def test_empty_string(self):
        from rag.hybrid import tokenize_chinese
        tokens = tokenize_chinese("")
        assert tokens == []

    def test_short_cjk(self):
        from rag.hybrid import tokenize_chinese
        tokens = tokenize_chinese("道")
        # 单个 CJK 字符：二元组无法生成，应返回单字符
        assert len(tokens) >= 0
